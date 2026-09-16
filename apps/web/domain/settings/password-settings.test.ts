import { ApiError, type Me } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import PasswordSettings from './password-settings.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { getMe: vi.fn(), changePassword: vi.fn() } }
}));

const api = vi.mocked(lumia.user);

function me(overrides: Partial<Me> = {}): Me {
	return {
		id: 'user-1',
		email: 'lecteur@example.test',
		role: 'member',
		password_set: true,
		preferred_language: 'fr',
		...overrides
	} as Me;
}

function panel() {
	const { container } = render(PasswordSettings);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		form: () => q<HTMLFormElement>('[data-test-password-form]')!,
		current: () => q<HTMLInputElement>('[data-test-current-password]'),
		newPassword: () => q<HTMLInputElement>('[data-test-new-password]')!,
		confirmation: () => q<HTMLInputElement>('[data-test-confirm-password]')!,
		error: () => q('[data-test-password-error]'),
		submit: () => q<HTMLButtonElement>('[data-test-password-submit]')!
	};
}

async function loaded(account: Me = me()) {
	api.getMe.mockResolvedValue(account);
	const view = panel();
	await vi.waitFor(() => expect(view.current() !== null).toBe(account.password_set));
	return view;
}

async function fill(
	view: ReturnType<typeof panel>,
	{ current = 'correct-horse', next = 'battery-staple', confirmation = next } = {}
) {
	if (view.current()) await fireEvent.input(view.current()!, { target: { value: current } });
	await fireEvent.input(view.newPassword(), { target: { value: next } });
	await fireEvent.input(view.confirmation(), { target: { value: confirmation } });
}

beforeEach(() => {
	api.getMe.mockReset();
	api.changePassword.mockReset();
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.clearAllMocks();
});

describe('changing the password', () => {
	it('sends the current one alongside the new one', async () => {
		api.changePassword.mockResolvedValue(undefined);
		const view = await loaded();

		await fill(view);
		await fireEvent.submit(view.form());

		await vi.waitFor(() =>
			expect(api.changePassword).toHaveBeenCalledWith('correct-horse', 'battery-staple')
		);
	});

	it('confirms the change', async () => {
		api.changePassword.mockResolvedValue(undefined);
		const view = await loaded();

		await fill(view);
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
	});

	// Leaving the typed passwords in the fields of a screen that stays open is an invitation for
	// the next person at the keyboard to read them off it.
	it('clears the fields once the change went through', async () => {
		api.changePassword.mockResolvedValue(undefined);
		const view = await loaded();

		await fill(view);
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(view.newPassword().value).toBe(''));
		expect(view.current()?.value).toBe('');
	});

	it('keeps every password out of sight while it is typed', async () => {
		const view = await loaded();

		expect(view.current()?.type).toBe('password');
		expect(view.newPassword().type).toBe('password');
		expect(view.confirmation().type).toBe('password');
	});

	it('refuses two new passwords that differ, without calling the api', async () => {
		const view = await loaded();

		await fill(view, { confirmation: 'battery-stapel' });
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(api.changePassword).not.toHaveBeenCalled();
	});

	it('refuses a password under the minimum length, without calling the api', async () => {
		const view = await loaded();

		await fill(view, { next: 'short1' });
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(api.changePassword).not.toHaveBeenCalled();
	});

	// A 401 here is the current password, not the session: the request carried a valid token.
	it('names the current password when the api refuses it', async () => {
		api.changePassword.mockRejectedValue(new ApiError(401, undefined));
		const view = await loaded();

		await fill(view);
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('lets the change be tried again after a failure', async () => {
		api.changePassword.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fill(view);
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.submit().disabled).toBe(false);
	});
});

describe('an account that has no password yet', () => {
	// SSO and magic-link accounts never had one: a required "current password" field would be a
	// door with no key, on the only screen that could give them one.
	it('asks for no current password', async () => {
		const view = await loaded(me({ password_set: false }));

		expect(view.current()).toBeNull();
	});

	it('sends no current password at all', async () => {
		api.changePassword.mockResolvedValue(undefined);
		const view = await loaded(me({ password_set: false }));

		await fill(view);
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(api.changePassword).toHaveBeenCalledWith(null, 'battery-staple'));
	});

	it('asks for the current one from the next change on', async () => {
		api.changePassword.mockResolvedValue(undefined);
		const view = await loaded(me({ password_set: false }));

		await fill(view);
		await fireEvent.submit(view.form());

		await vi.waitFor(() => expect(view.current()).not.toBeNull());
	});
});
