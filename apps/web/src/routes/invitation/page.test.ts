import { goto } from '$app/navigation';
import { ApiError } from '@lumia/core';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import InvitationPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

let searchParams = new URLSearchParams();
vi.mock('$app/state', () => ({
	page: {
		get url() {
			return { searchParams };
		}
	}
}));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { acceptInvitation: vi.fn() } }
}));

const api = vi.mocked(lumia.user);

function invitationPage() {
	const { container } = render(InvitationPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		form: () => q<HTMLFormElement>('[data-test-invitation-form]'),
		unusable: () => q('[data-test-invitation-unusable]'),
		signInLink: () => q<HTMLAnchorElement>('[data-test-sign-in-link]'),
		error: () => q('[data-test-invitation-error]'),
		username: () => q<HTMLInputElement>('[data-test-username]')!,
		password: () => q<HTMLInputElement>('[data-test-password]')!,
		confirmation: () => q<HTMLInputElement>('[data-test-confirm-password]')!
	};
}

async function filled(username: string, password: string, confirmation = password) {
	const view = invitationPage();
	await waitFor(() => expect(view.form()).not.toBeNull());
	await fireEvent.input(view.username(), { target: { value: username } });
	await fireEvent.input(view.password(), { target: { value: password } });
	await fireEvent.input(view.confirmation(), { target: { value: confirmation } });
	return view;
}

beforeEach(() => {
	searchParams = new URLSearchParams({ token: 'the-token' });
	api.acceptInvitation.mockReset();
});

afterEach(() => {
	vi.mocked(goto).mockClear();
});

describe('arriving from the emailed link', () => {
	it('shows the form when the link carries a token', async () => {
		const view = invitationPage();

		await waitFor(() => expect(view.form()).not.toBeNull());
		expect(view.unusable()).toBeNull();
	});

	// Without the token no account can be created, so the page says where the link comes from
	// rather than offering a form whose submit could only ever fail.
	it('asks for the emailed link when the address carries no token', async () => {
		searchParams = new URLSearchParams();
		const view = invitationPage();

		await waitFor(() => expect(view.unusable()).not.toBeNull());
		expect(view.unusable()!.getAttribute('role')).toBe('status');
		expect(view.form()).toBeNull();
	});

	// The token is a credential: left in the address bar it ends up in the history and in any
	// screenshot of the page.
	it('takes the token out of the address bar once read', async () => {
		history.replaceState(null, '', '/invitation?token=the-token');
		const view = invitationPage();

		await waitFor(() => expect(view.form()).not.toBeNull());
		expect(window.location.search).toBe('');
	});

	it('ties the length rule to the password field, so a screen reader announces it', async () => {
		const view = invitationPage();
		await waitFor(() => expect(view.form()).not.toBeNull());

		const hintId = view.password().getAttribute('aria-describedby')!;
		expect(document.getElementById(hintId)?.textContent).toMatch(/\d/);
	});
});

describe('creating the account', () => {
	it('sends the token, the username and the password, then opens the app', async () => {
		api.acceptInvitation.mockResolvedValue(undefined);
		const view = await filled('lena', 'battery-staple');

		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(goto).toHaveBeenCalled());

		expect(api.acceptInvitation).toHaveBeenCalledWith('the-token', 'lena', 'battery-staple');
		expect(String(vi.mocked(goto).mock.calls[0][0])).toMatch(/\/articles$/);
	});

	it('drops the spaces a paste leaves around the username', async () => {
		api.acceptInvitation.mockResolvedValue(undefined);
		const view = await filled('  lena ', 'battery-staple');

		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(goto).toHaveBeenCalled());

		expect(api.acceptInvitation).toHaveBeenCalledWith('the-token', 'lena', 'battery-staple');
	});

	it('refuses a password under the minimum length, without spending the invitation', async () => {
		const view = await filled('lena', 'short1');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.error()!.getAttribute('role')).toBe('alert');
		expect(api.acceptInvitation).not.toHaveBeenCalled();
	});

	it('refuses two passwords that differ, without spending the invitation', async () => {
		const view = await filled('lena', 'battery-staple', 'battery-stapel');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(api.acceptInvitation).not.toHaveBeenCalled();
	});
});

describe('an invitation that can no longer be used', () => {
	// Expired, already accepted, revoked and unknown tokens all come back as the same 401. None of
	// them can be fixed from the form, so it goes away and the reader is told to ask for a new one.
	it('replaces the form with an alert and a way to sign in', async () => {
		api.acceptInvitation.mockRejectedValue(new ApiError(401, undefined));
		const view = await filled('lena', 'battery-staple');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.unusable()).not.toBeNull());
		expect(view.unusable()!.getAttribute('role')).toBe('alert');
		expect(view.form()).toBeNull();
		expect(view.signInLink()!.getAttribute('href')).toMatch(/\/login$/);
		expect(goto).not.toHaveBeenCalled();
	});

	it('says something different from the missing-link message', async () => {
		searchParams = new URLSearchParams();
		const missing = invitationPage();
		await waitFor(() => expect(missing.unusable()).not.toBeNull());
		const missingText = missing.unusable()!.textContent;

		searchParams = new URLSearchParams({ token: 'the-token' });
		api.acceptInvitation.mockRejectedValue(new ApiError(401, undefined));
		const view = await filled('lena', 'battery-staple');
		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(view.unusable()).not.toBeNull());

		expect(view.unusable()!.textContent).not.toBe(missingText);
	});
});

describe('a refusal the form can survive', () => {
	it('points to the admin when the address is taken or the instance is full', async () => {
		api.acceptInvitation.mockRejectedValue(new ApiError(409, undefined));
		const view = await filled('lena', 'battery-staple');

		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(view.error()).not.toBeNull());
		const conflictText = view.error()!.textContent;

		api.acceptInvitation.mockRejectedValue(new Error('offline'));
		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(view.error()!.textContent).not.toBe(conflictText));
		expect(goto).not.toHaveBeenCalled();
	});

	it('lets the account be created again after a failure', async () => {
		api.acceptInvitation.mockRejectedValue(new Error('offline'));
		const view = await filled('lena', 'battery-staple');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.form()!.querySelector('button')!.disabled).toBe(false);
	});
});
