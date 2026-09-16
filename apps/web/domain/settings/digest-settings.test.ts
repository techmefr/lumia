import type { Me } from '@lumia/core';
import { fireEvent, render } from '@testing-library/svelte';
import { beforeEach, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import DigestSettings from './digest-settings.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { getMe: vi.fn(), updateMe: vi.fn() } }
}));

const api = vi.mocked(lumia.user);

function me(overrides: Partial<Me> = {}): Me {
	return {
		id: 'user-1',
		email: 'lecteur@example.test',
		role: 'user',
		preferred_language: 'fr',
		digest_frequency: 'never',
		digest_hour: 8,
		digest_timezone: 'Europe/Paris',
		...overrides
	} as Me;
}

function panel() {
	const { container } = render(DigestSettings);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		frequency: () => q<HTMLSelectElement>('[data-test-digest-frequency]'),
		hour: () => q<HTMLSelectElement>('[data-test-digest-hour]'),
		error: () => q('[data-test-digest-error]'),
		save: () => q<HTMLButtonElement>('[data-test-digest-save]')!
	};
}

async function loaded(account: Me = me()) {
	api.getMe.mockResolvedValue(account);
	const view = panel();
	await vi.waitFor(() => expect(view.frequency()).not.toBeNull());
	return view;
}

beforeEach(() => {
	vi.clearAllMocks();
});

it('opens on never, so an account that never asked is never subscribed', async () => {
	const view = await loaded();

	expect(view.frequency()!.value).toBe('never');
	// Nothing to schedule while the digest is off, so the hour is not asked for.
	expect(view.hour()).toBeNull();
});

it('asks for an hour only once a frequency is chosen', async () => {
	const view = await loaded(me({ digest_frequency: 'daily', digest_hour: 7 }));

	expect(view.hour()!.value).toBe('7');
});

it('sends the chosen frequency, hour and the browser timezone', async () => {
	const view = await loaded(me({ digest_frequency: 'daily' }));
	api.updateMe.mockResolvedValue(me({ digest_frequency: 'weekly', digest_hour: 19 }));

	await fireEvent.change(view.frequency()!, { target: { value: 'weekly' } });
	await fireEvent.change(view.hour()!, { target: { value: '19' } });
	await fireEvent.click(view.save());

	await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalledTimes(1));
	const payload = api.updateMe.mock.calls[0][0];
	expect(payload.digest_frequency).toBe('weekly');
	expect(payload.digest_hour).toBe(19);
	expect(payload.digest_timezone).toBeTruthy();
});

it('turning it off is one choice away and goes through the same save', async () => {
	const view = await loaded(me({ digest_frequency: 'daily' }));
	api.updateMe.mockResolvedValue(me({ digest_frequency: 'never' }));

	await fireEvent.change(view.frequency()!, { target: { value: 'never' } });
	await fireEvent.click(view.save());

	await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalledTimes(1));
	expect(api.updateMe.mock.calls[0][0].digest_frequency).toBe('never');
});

it('says so when the settings cannot be loaded', async () => {
	api.getMe.mockRejectedValue(new Error('offline'));
	const view = panel();

	await vi.waitFor(() => expect(view.error()).not.toBeNull());
});
