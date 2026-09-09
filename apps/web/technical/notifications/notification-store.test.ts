import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
	getNotificationSettings,
	isQuietHour,
	notificationFor,
	permissionState,
	requestPermission,
	updateNotificationSettings,
	type NotificationSettings
} from './notification-store.svelte';
import { setLocale } from '../i18n/i18n.svelte';

const AWAKE = new Date('2026-09-09T14:00:00');

function settings(overrides: Partial<NotificationSettings> = {}): NotificationSettings {
	return {
		enabled: true,
		intervalMinutes: 30,
		threshold: 3,
		quietFromHour: 22,
		quietToHour: 8,
		...overrides
	};
}

describe('isQuietHour', () => {
	it('is never quiet when both bounds are the same hour', () => {
		expect(isQuietHour(new Date('2026-09-09T03:00:00'), 8, 8)).toBe(false);
	});

	describe('a window inside one day', () => {
		it('is quiet on the opening hour', () => {
			expect(isQuietHour(new Date('2026-09-09T09:00:00'), 9, 17)).toBe(true);
		});

		it('is quiet in the middle', () => {
			expect(isQuietHour(new Date('2026-09-09T13:00:00'), 9, 17)).toBe(true);
		});

		it('is awake again on the closing hour, which is exclusive', () => {
			expect(isQuietHour(new Date('2026-09-09T17:00:00'), 9, 17)).toBe(false);
		});

		it('is awake before it opens', () => {
			expect(isQuietHour(new Date('2026-09-09T08:59:00'), 9, 17)).toBe(false);
		});
	});

	describe('a window wrapping past midnight', () => {
		it('is quiet on the opening hour, before midnight', () => {
			expect(isQuietHour(new Date('2026-09-09T22:00:00'), 22, 8)).toBe(true);
		});

		it('is quiet after midnight', () => {
			expect(isQuietHour(new Date('2026-09-09T03:00:00'), 22, 8)).toBe(true);
		});

		it('is awake on the closing hour', () => {
			expect(isQuietHour(new Date('2026-09-09T08:00:00'), 22, 8)).toBe(false);
		});

		it('is awake in the middle of the afternoon', () => {
			expect(isQuietHour(new Date('2026-09-09T15:00:00'), 22, 8)).toBe(false);
		});
	});
});

describe('notificationFor', () => {
	beforeEach(() => {
		setLocale('en');
	});

	it('says nothing on the very first poll, so enabling never announces the backlog', () => {
		expect(notificationFor(120, null, settings(), AWAKE)).toBeNull();
	});

	it('says nothing when the unread total has not moved', () => {
		expect(notificationFor(40, 40, settings(), AWAKE)).toBeNull();
	});

	it('says nothing when the total went down because articles were read elsewhere', () => {
		expect(notificationFor(12, 40, settings(), AWAKE)).toBeNull();
	});

	it('stays silent below the threshold', () => {
		expect(notificationFor(42, 40, settings({ threshold: 3 }), AWAKE)).toBeNull();
	});

	it('speaks exactly on the threshold', () => {
		expect(notificationFor(43, 40, settings({ threshold: 3 }), AWAKE)).not.toBeNull();
	});

	it('counts the new articles rather than the total', () => {
		expect(notificationFor(140, 100, settings({ threshold: 3 }), AWAKE)).toContain('40');
	});

	it('uses the singular wording when a threshold of one lets a lone article through', () => {
		const message = notificationFor(41, 40, settings({ threshold: 1 }), AWAKE);
		expect(message).toBe('1 new article to read');
	});

	it('uses the plural wording beyond one', () => {
		expect(notificationFor(45, 40, settings({ threshold: 1 }), AWAKE)).toBe(
			'5 new articles to read'
		);
	});

	it('stays silent during quiet hours even with plenty of new articles', () => {
		const night = new Date('2026-09-09T02:00:00');
		expect(notificationFor(200, 40, settings({ quietFromHour: 22, quietToHour: 8 }), night)).toBeNull();
	});

	it('speaks at the same volume once the quiet window closes', () => {
		const morning = new Date('2026-09-09T08:00:00');
		expect(
			notificationFor(200, 40, settings({ quietFromHour: 22, quietToHour: 8 }), morning)
		).not.toBeNull();
	});

	it('follows the interface language, so a message never lags a language change', () => {
		setLocale('fr');
		const french = notificationFor(45, 40, settings({ threshold: 1 }), AWAKE);
		setLocale('en');
		const english = notificationFor(45, 40, settings({ threshold: 1 }), AWAKE);
		expect(french).not.toBe(english);
	});
});

describe('notification settings', () => {
	it('starts disabled, so nothing is ever shown before the reader asks', () => {
		expect(getNotificationSettings().enabled).toBe(false);
	});

	it('keeps the untouched fields when one is patched', () => {
		const before = getNotificationSettings().threshold;
		updateNotificationSettings({ intervalMinutes: 60 });
		expect(getNotificationSettings()).toMatchObject({ intervalMinutes: 60, threshold: before });
	});

	it('writes the change through, so a reload finds the same choice', () => {
		updateNotificationSettings({ intervalMinutes: 180, threshold: 7 });
		expect(JSON.parse(localStorage.getItem('lumia-notifications') ?? '{}')).toMatchObject({
			intervalMinutes: 180,
			threshold: 7
		});
	});
});

/**
 * The Notification api is the outer boundary: jsdom has none, and the store's whole job is deciding
 * whether to call it. The stub records what was shown and lets the test say what the browser
 * answered when permission was asked for.
 */
function fakeNotifications(permission: NotificationPermission, answer = permission) {
	const shown: Array<{ title: string; body?: string; tag?: string }> = [];

	class FakeNotification {
		static permission = permission;
		static requestPermission = async () => {
			FakeNotification.permission = answer;
			return answer;
		};
		constructor(title: string, options: NotificationOptions = {}) {
			shown.push({ title, body: options.body, tag: options.tag });
		}
	}

	vi.stubGlobal('Notification', FakeNotification);
	return shown;
}

function whileLookingElsewhere() {
	Object.defineProperty(document, 'visibilityState', {
		configurable: true,
		get: () => 'hidden'
	});
}

describe('the stored settings', () => {
	// The store is a module singleton that reads localStorage once, at import: each case here needs
	// a fresh one, or it inherits whatever the previous test saved.
	beforeEach(() => {
		localStorage.clear();
		vi.resetModules();
	});

	afterEach(() => {
		localStorage.clear();
		vi.resetModules();
	});

	it('starts from the defaults', async () => {
		const store = await import('./notification-store.svelte');

		expect(store.getNotificationSettings()).toEqual({
			enabled: false,
			intervalMinutes: 30,
			threshold: 3,
			quietFromHour: 22,
			quietToHour: 8
		});
	});

	it('keeps what was saved', async () => {
		const store = await import('./notification-store.svelte');

		store.updateNotificationSettings({ threshold: 10 });

		expect(store.getNotificationSettings().threshold).toBe(10);
	});

	it('survives a reload', async () => {
		const first = await import('./notification-store.svelte');
		first.updateNotificationSettings({ intervalMinutes: 180, enabled: true });

		vi.resetModules();
		const second = await import('./notification-store.svelte');

		expect(second.getNotificationSettings().intervalMinutes).toBe(180);
		expect(second.getNotificationSettings().enabled).toBe(true);
	});

	it('changes only what the patch mentions', async () => {
		const store = await import('./notification-store.svelte');

		store.updateNotificationSettings({ threshold: 1 });

		expect(store.getNotificationSettings().intervalMinutes).toBe(30);
	});

	// A version of the app that stored fewer fields, or a hand-edited value: the settings screen
	// must not end up with an undefined interval, which would make setInterval fire continuously.
	it('fills in the fields a stored version did not have', async () => {
		localStorage.setItem('lumia-notifications', JSON.stringify({ enabled: true }));
		vi.resetModules();

		const store = await import('./notification-store.svelte');

		expect(store.getNotificationSettings().enabled).toBe(true);
		expect(store.getNotificationSettings().intervalMinutes).toBe(30);
	});

	it('falls back to the defaults when what was stored is not readable', async () => {
		localStorage.setItem('lumia-notifications', 'not json');
		vi.resetModules();

		const store = await import('./notification-store.svelte');

		expect(store.getNotificationSettings().intervalMinutes).toBe(30);
	});

	// Private browsing throws on write. Losing the setting at the next reload is acceptable;
	// throwing in the settings screen is not.
	it('does not throw when the storage refuses to keep it', async () => {
		const store = await import('./notification-store.svelte');
		const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('quota');
		});

		expect(() => store.updateNotificationSettings({ threshold: 5 })).not.toThrow();
		expect(store.getNotificationSettings().threshold).toBe(5);

		setItem.mockRestore();
	});
});

describe('the browser permission', () => {
	afterEach(() => {
		vi.unstubAllGlobals();
	});

	// 'unsupported' is not the same as 'denied': one is a browser that cannot notify, the other a
	// reader who said no. The settings screen says something different for each.
	it('reports a browser without the api as unsupported', () => {
		expect(permissionState()).toBe('unsupported');
	});

	it.each(['default', 'granted', 'denied'] as const)('reports %s as it stands', (state) => {
		fakeNotifications(state);

		expect(permissionState()).toBe(state);
	});

	it('answers unsupported rather than asking a browser that cannot notify', async () => {
		expect(await requestPermission()).toBe('unsupported');
	});

	it('asks the browser and reports what it answered', async () => {
		fakeNotifications('default', 'granted');

		expect(await requestPermission()).toBe('granted');
	});

	it('reports a refusal', async () => {
		fakeNotifications('default', 'denied');

		expect(await requestPermission()).toBe('denied');
	});
});

describe('polling for new articles', () => {
	let stop: (() => void) | null = null;

	beforeEach(() => {
		vi.useFakeTimers();
		localStorage.clear();
	});

	afterEach(() => {
		stop?.();
		stop = null;
		vi.useRealTimers();
		vi.unstubAllGlobals();
		vi.resetModules();
		localStorage.clear();
	});

	async function start(
		total: number | (() => Promise<number>),
		settings: Partial<NotificationSettings> = {}
	) {
		const store = await import('./notification-store.svelte');
		const fetchTotal = typeof total === 'function' ? vi.fn(total) : vi.fn(async () => total);
		store.updateNotificationSettings({ enabled: true, threshold: 1, ...settings });
		stop = store.watchUnread(fetchTotal);
		return { store, fetchTotal };
	}

	it('does nothing at all while notifications are off', async () => {
		fakeNotifications('granted');
		const { fetchTotal } = await start(10, { enabled: false });

		await vi.advanceTimersByTimeAsync(60 * 60_000);

		expect(fetchTotal).not.toHaveBeenCalled();
	});

	// A permission revoked in the browser settings beats what the app stored: without this check,
	// every poll would construct a Notification the browser refuses.
	it('does nothing when the permission was revoked', async () => {
		fakeNotifications('denied');
		const { fetchTotal } = await start(10);

		await vi.advanceTimersByTimeAsync(60 * 60_000);

		expect(fetchTotal).not.toHaveBeenCalled();
	});

	// Turning notifications on must not announce the backlog that was already unread: the first
	// read only records where the counter stood.
	it('reads the counter once on start without notifying', async () => {
		const shown = fakeNotifications('granted');
		whileLookingElsewhere();
		const { fetchTotal } = await start(40);

		await vi.advanceTimersByTimeAsync(0);

		expect(fetchTotal).toHaveBeenCalledTimes(1);
		expect(shown).toHaveLength(0);
	});

	it('notifies when the counter has gone up since the last poll', async () => {
		const shown = fakeNotifications('granted');
		whileLookingElsewhere();
		let total = 40;
		await start(async () => total, { intervalMinutes: 15 });
		await vi.advanceTimersByTimeAsync(0);

		total = 45;
		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(shown).toHaveLength(1);
		expect(shown[0].body).toContain('5');
	});

	it('says nothing when the counter has not moved', async () => {
		const shown = fakeNotifications('granted');
		whileLookingElsewhere();
		await start(40, { intervalMinutes: 15 });
		await vi.advanceTimersByTimeAsync(0);

		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(shown).toHaveLength(0);
	});

	it('says nothing when fewer articles arrived than the threshold', async () => {
		const shown = fakeNotifications('granted');
		whileLookingElsewhere();
		let total = 40;
		await start(async () => total, { intervalMinutes: 15, threshold: 5 });
		await vi.advanceTimersByTimeAsync(0);

		total = 42;
		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(shown).toHaveLength(0);
	});

	// Looking at the app is not an interruption worth a system notification: the poll still runs,
	// but only to keep the baseline current so the next arrival is counted from here.
	it('does not notify while the tab is being looked at', async () => {
		const shown = fakeNotifications('granted');
		Object.defineProperty(document, 'visibilityState', {
			configurable: true,
			get: () => 'visible'
		});
		let total = 40;
		const { fetchTotal } = await start(async () => total, { intervalMinutes: 15 });
		await vi.advanceTimersByTimeAsync(0);

		total = 60;
		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(fetchTotal).toHaveBeenCalledTimes(2);
		expect(shown).toHaveLength(0);
	});

	it('groups its notifications under one tag, so they replace each other', async () => {
		const shown = fakeNotifications('granted');
		whileLookingElsewhere();
		let total = 40;
		await start(async () => total, { intervalMinutes: 15 });
		await vi.advanceTimersByTimeAsync(0);

		total = 50;
		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(shown[0].tag).toBe('lumia-unread');
	});

	it('polls at the frequency that was chosen', async () => {
		fakeNotifications('granted');
		whileLookingElsewhere();
		const { fetchTotal } = await start(40, { intervalMinutes: 60 });
		await vi.advanceTimersByTimeAsync(0);

		await vi.advanceTimersByTimeAsync(59 * 60_000);
		expect(fetchTotal).toHaveBeenCalledTimes(1);

		await vi.advanceTimersByTimeAsync(60_000);
		expect(fetchTotal).toHaveBeenCalledTimes(2);
	});

	// The reason the timer sits in an effect: saving a shorter frequency has to take effect now,
	// not at the next tab switch.
	it('follows a frequency changed while it is running', async () => {
		fakeNotifications('granted');
		whileLookingElsewhere();
		const { store, fetchTotal } = await start(40, { intervalMinutes: 180 });
		await vi.advanceTimersByTimeAsync(0);

		store.updateNotificationSettings({ intervalMinutes: 15 });
		await vi.advanceTimersByTimeAsync(0);
		const afterRestart = fetchTotal.mock.calls.length;

		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(fetchTotal.mock.calls.length).toBeGreaterThan(afterRestart);
	});

	// Offline, or logged out: the next tick tries again. A rejected fetch must not take the poll
	// down for the rest of the session.
	it('keeps polling after a failed read', async () => {
		fakeNotifications('granted');
		whileLookingElsewhere();
		let fail = true;
		const { fetchTotal } = await start(
			async () => {
				if (fail) throw new Error('offline');
				return 40;
			},
			{ intervalMinutes: 15 }
		);
		await vi.advanceTimersByTimeAsync(0);

		fail = false;
		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(fetchTotal.mock.calls.length).toBeGreaterThan(1);
	});

	it('stops polling when the caller tears it down', async () => {
		fakeNotifications('granted');
		whileLookingElsewhere();
		const { fetchTotal } = await start(40, { intervalMinutes: 15 });
		await vi.advanceTimersByTimeAsync(0);
		const before = fetchTotal.mock.calls.length;

		stop?.();
		stop = null;
		await vi.advanceTimersByTimeAsync(60 * 60_000);

		expect(fetchTotal.mock.calls.length).toBe(before);
	});

	it('stops notifying once notifications are turned off', async () => {
		const shown = fakeNotifications('granted');
		whileLookingElsewhere();
		let total = 40;
		const { store } = await start(async () => total, { intervalMinutes: 15 });
		await vi.advanceTimersByTimeAsync(0);

		store.updateNotificationSettings({ enabled: false });
		total = 90;
		await vi.advanceTimersByTimeAsync(15 * 60_000);

		expect(shown).toHaveLength(0);
	});
});
