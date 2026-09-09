import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
	getNotificationSettings,
	updateNotificationSettings
} from '$technical/notifications/notification-store.svelte';
import NotificationSettings from './notification-settings.svelte';

/**
 * The Notification api is the outer boundary: jsdom has none, and the screen's whole job is to ask
 * for permission and then remember what was chosen.
 */
function browserWhere(permission: NotificationPermission | 'unsupported', answer = permission) {
	if (permission === 'unsupported') {
		vi.stubGlobal('Notification', undefined);
		return;
	}
	class FakeNotification {
		static permission = permission;
		static requestPermission = async () => {
			FakeNotification.permission = answer === 'unsupported' ? 'denied' : answer;
			return FakeNotification.permission;
		};
	}
	vi.stubGlobal('Notification', FakeNotification);
}

function screen() {
	const { container } = render(NotificationSettings);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		toggle: () => q<HTMLButtonElement>('[data-test-notif-toggle]')!,
		save: () => q<HTMLButtonElement>('[data-test-notif-save]')!,
		interval: () => q<HTMLSelectElement>('[data-test-notif-interval]')!,
		threshold: () => q<HTMLSelectElement>('[data-test-notif-threshold]')!,
		quietFrom: () => q<HTMLSelectElement>('[data-test-notif-quiet-from]')!,
		quietTo: () => q<HTMLSelectElement>('[data-test-notif-quiet-to]')!,
		unsupported: () => q('[data-test-notif-unsupported]'),
		denied: () => q('[data-test-notif-denied]')
	};
}

beforeEach(() => {
	localStorage.clear();
	updateNotificationSettings({
		enabled: false,
		intervalMinutes: 30,
		threshold: 3,
		quietFromHour: 22,
		quietToHour: 8
	});
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.unstubAllGlobals();
});

describe('what the browser allows', () => {
	// Three different situations, three different things to say: a browser that cannot notify, a
	// reader who refused, and a choice not yet made. Lumping them together would leave someone
	// staring at a dead button with no explanation.
	it('says so when the browser cannot notify at all', async () => {
		browserWhere('unsupported');
		const view = screen();

		await vi.waitFor(() => expect(view.unsupported()).not.toBeNull());
		expect(view.toggle().disabled).toBe(true);
	});

	it('says so when the reader refused', async () => {
		browserWhere('denied');
		const view = screen();

		await vi.waitFor(() => expect(view.denied()).not.toBeNull());
		expect(view.toggle().disabled).toBe(true);
	});

	it('says nothing and offers the switch when the choice is still open', async () => {
		browserWhere('default');
		const view = screen();

		await vi.waitFor(() => expect(view.toggle().disabled).toBe(false));
		expect(view.unsupported()).toBeNull();
		expect(view.denied()).toBeNull();
	});
});

describe('turning notifications on', () => {
	it('asks the browser only when the switch is pressed', async () => {
		browserWhere('default', 'granted');
		const view = screen();
		await vi.waitFor(() => expect(view.toggle().disabled).toBe(false));
		expect(getNotificationSettings().enabled).toBe(false);

		await fireEvent.click(view.toggle());

		await vi.waitFor(() => expect(getNotificationSettings().enabled).toBe(true));
	});

	it('confirms it', async () => {
		browserWhere('default', 'granted');
		const view = screen();
		await vi.waitFor(() => expect(view.toggle().disabled).toBe(false));

		await fireEvent.click(view.toggle());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('default');
	});

	// A refusal at the browser prompt must not leave the app thinking notifications are on: it
	// would poll forever and never manage to show one.
	it('stays off and says so when the browser prompt is refused', async () => {
		browserWhere('default', 'denied');
		const view = screen();
		await vi.waitFor(() => expect(view.toggle().disabled).toBe(false));

		await fireEvent.click(view.toggle());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
		expect(getNotificationSettings().enabled).toBe(false);
	});

	it('disables the switch once the browser has refused', async () => {
		browserWhere('default', 'denied');
		const view = screen();
		await vi.waitFor(() => expect(view.toggle().disabled).toBe(false));

		await fireEvent.click(view.toggle());

		await vi.waitFor(() => expect(view.toggle().disabled).toBe(true));
	});
});

describe('turning them off', () => {
	it('does not ask the browser again', async () => {
		browserWhere('granted');
		updateNotificationSettings({ enabled: true });
		const view = screen();
		await vi.waitFor(() => expect(view.toggle().textContent).toBeTruthy());

		await fireEvent.click(view.toggle());

		await vi.waitFor(() => expect(getNotificationSettings().enabled).toBe(false));
	});

	it('can be turned back on', async () => {
		browserWhere('granted');
		updateNotificationSettings({ enabled: true });
		const view = screen();
		await vi.waitFor(() => expect(view.toggle()).not.toBeNull());

		await fireEvent.click(view.toggle());
		await vi.waitFor(() => expect(getNotificationSettings().enabled).toBe(false));
		await fireEvent.click(view.toggle());

		await vi.waitFor(() => expect(getNotificationSettings().enabled).toBe(true));
	});
});

describe('what the screen shows on arrival', () => {
	it('shows the settings that were saved', async () => {
		browserWhere('granted');
		updateNotificationSettings({
			intervalMinutes: 180,
			threshold: 10,
			quietFromHour: 23,
			quietToHour: 6
		});
		const view = screen();

		await vi.waitFor(() => expect(view.interval().value).toBe('180'));
		expect(view.threshold().value).toBe('10');
		expect(view.quietFrom().value).toBe('23');
		expect(view.quietTo().value).toBe('6');
	});

	// A permission revoked in the browser settings beats what the app stored: showing the switch as
	// on would be a promise the browser will not keep.
	it('shows notifications as off when the permission was revoked', async () => {
		browserWhere('denied');
		updateNotificationSettings({ enabled: true });
		const view = screen();

		await vi.waitFor(() => expect(view.denied()).not.toBeNull());
		expect(view.toggle().disabled).toBe(true);
	});
});

describe('saving the settings', () => {
	it('keeps what was chosen', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.interval()).not.toBeNull());

		await fireEvent.change(view.interval(), { target: { value: '60' } });
		await fireEvent.change(view.threshold(), { target: { value: '5' } });
		await fireEvent.change(view.quietFrom(), { target: { value: '21' } });
		await fireEvent.change(view.quietTo(), { target: { value: '7' } });
		await fireEvent.click(view.save());

		expect(getNotificationSettings()).toMatchObject({
			intervalMinutes: 60,
			threshold: 5,
			quietFromHour: 21,
			quietToHour: 7
		});
	});

	it('confirms the save', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.save()).not.toBeNull());

		await fireEvent.click(view.save());

		expect(toasts.toasts).toHaveLength(1);
	});

	// Saving a frequency must not turn notifications on by itself: the switch is the only thing
	// that asks for permission, and enabling without it would poll with no permission at all.
	it('leaves the switch alone', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.save()).not.toBeNull());

		await fireEvent.click(view.save());

		expect(getNotificationSettings().enabled).toBe(false);
	});
});

describe('the choices it offers', () => {
	it('offers the four polling frequencies', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.interval()).not.toBeNull());

		expect([...view.interval().options].map((option) => option.value)).toEqual([
			'15',
			'30',
			'60',
			'180'
		]);
	});

	it('offers the four thresholds, including notifying on the first article', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.threshold()).not.toBeNull());

		expect([...view.threshold().options].map((option) => option.value)).toEqual([
			'1',
			'3',
			'5',
			'10'
		]);
	});

	it('offers every hour of the day on both ends of the quiet window', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.quietFrom()).not.toBeNull());

		expect(view.quietFrom().options).toHaveLength(24);
		expect(view.quietTo().options).toHaveLength(24);
	});

	// Padded to two digits, because a column of "9:00" and "22:00" does not line up and reads badly
	// on a phone.
	it('shows the hours on a 24-hour clock', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.quietFrom()).not.toBeNull());

		expect(view.quietFrom().options[0].textContent?.trim()).toBe('00:00');
		expect(view.quietFrom().options[9].textContent?.trim()).toBe('09:00');
	});

	// The selects carry the settings, so they have to be reachable and named: a label that points
	// nowhere is the usual way a form like this becomes unusable with a screen reader.
	it('labels the frequency and the threshold', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.interval()).not.toBeNull());

		for (const id of ['notif-interval', 'notif-threshold']) {
			expect(view.container.querySelector(`label[for="${id}"]`)).not.toBeNull();
		}
	});

	it('groups the quiet hours under a legend', async () => {
		browserWhere('granted');
		const view = screen();
		await vi.waitFor(() => expect(view.quietFrom()).not.toBeNull());

		expect(view.container.querySelector('fieldset legend')?.textContent?.trim()).toBeTruthy();
	});
});
