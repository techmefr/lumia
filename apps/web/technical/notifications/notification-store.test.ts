import { beforeEach, describe, expect, it } from 'vitest';
import {
	getNotificationSettings,
	isQuietHour,
	notificationFor,
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
