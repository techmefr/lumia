import { goto } from '$app/navigation';
import { ApiError } from '@lumia/core';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import ResetPasswordPage from './+page.svelte';

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
	lumia: { user: { resetPassword: vi.fn() } }
}));

const api = vi.mocked(lumia.user);

function resetPage() {
	const { container } = render(ResetPasswordPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		form: () => q<HTMLFormElement>('[data-test-reset-form]'),
		missingLink: () => q('[data-test-missing-link]'),
		error: () => q('[data-test-reset-error]'),
		totpCode: () => q<HTMLInputElement>('[data-test-totp-code]'),
		newPassword: () => q<HTMLInputElement>('[data-test-new-password]')!,
		confirmation: () => q<HTMLInputElement>('[data-test-confirm-password]')!
	};
}

async function filled(newPassword: string, confirmation = newPassword) {
	const view = resetPage();
	await waitFor(() => expect(view.form()).not.toBeNull());
	await fireEvent.input(view.newPassword(), { target: { value: newPassword } });
	await fireEvent.input(view.confirmation(), { target: { value: confirmation } });
	return view;
}

beforeEach(() => {
	searchParams = new URLSearchParams({ magic_token: 'the-token' });
	api.resetPassword.mockReset();
});

afterEach(() => {
	vi.mocked(goto).mockClear();
});

describe('arriving from the emailed link', () => {
	it('shows the form when the link carries a token', async () => {
		const view = resetPage();

		await waitFor(() => expect(view.form()).not.toBeNull());
	});

	// Nothing can be reset without the token, so the page says where it comes from rather than
	// offering a form whose submit could only ever fail.
	it('asks for the emailed link when the address carries no token', async () => {
		searchParams = new URLSearchParams();
		const view = resetPage();

		await waitFor(() => expect(view.missingLink()).not.toBeNull());
		expect(view.form()).toBeNull();
	});
});

describe('choosing the new password', () => {
	it('sends the token and the password, then opens the app', async () => {
		api.resetPassword.mockResolvedValue(undefined);
		const view = await filled('battery-staple');

		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(goto).toHaveBeenCalled());

		expect(api.resetPassword).toHaveBeenCalledWith('the-token', 'battery-staple', {});
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/articles');
	});

	// Caught here rather than by the server, which sees only one of the two fields and would
	// happily store a password the reader mistyped twice over.
	it('refuses two passwords that differ, without calling the api', async () => {
		const view = await filled('battery-staple', 'battery-stapel');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(api.resetPassword).not.toHaveBeenCalled();
	});

	it('refuses a password under the minimum length, without calling the api', async () => {
		const view = await filled('short1');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(api.resetPassword).not.toHaveBeenCalled();
	});

	// A refused token means the link was spent or has expired; telling the reader their password
	// is wrong would send them looking in the wrong place.
	it('blames the link when the token is refused', async () => {
		api.resetPassword.mockRejectedValue(new ApiError(401, undefined));
		const view = await filled('battery-staple');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(goto).not.toHaveBeenCalled();
	});

	it('lets the reset be tried again after a failure', async () => {
		api.resetPassword.mockRejectedValue(new Error('offline'));
		const view = await filled('battery-staple');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		const button = view.form()!.querySelector('button')!;
		expect(button.disabled).toBe(false);
	});
});

// A reset hands back a signed-in session, so a mailbox on its own must not be a way past the
// authenticator the reader turned on.
describe('an account with a second factor', () => {
	function refused(detail: string) {
		return new ApiError(401, { detail });
	}

	it('asks for a code rather than blaming the link', async () => {
		api.resetPassword.mockRejectedValue(refused('totp_required'));
		const view = await filled('battery-staple');

		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.totpCode()).not.toBeNull());
		expect(view.error()).toBeNull();
		expect(goto).not.toHaveBeenCalled();
	});

	it('sends the code with the retry', async () => {
		api.resetPassword
			.mockRejectedValueOnce(refused('totp_required'))
			.mockResolvedValueOnce(undefined);
		const view = await filled('battery-staple');
		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(view.totpCode()).not.toBeNull());

		await fireEvent.input(view.totpCode()!, { target: { value: '123456' } });
		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(goto).toHaveBeenCalled());

		expect(api.resetPassword).toHaveBeenLastCalledWith('the-token', 'battery-staple', {
			totp_code: '123456'
		});
	});

	it('keeps asking and says so when the code is wrong', async () => {
		api.resetPassword
			.mockRejectedValueOnce(refused('totp_required'))
			.mockRejectedValueOnce(refused('invalid_totp_code'));
		const view = await filled('battery-staple');
		await fireEvent.submit(view.form()!);
		await waitFor(() => expect(view.totpCode()).not.toBeNull());

		await fireEvent.input(view.totpCode()!, { target: { value: '000000' } });
		await fireEvent.submit(view.form()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.totpCode()).not.toBeNull();
		expect(goto).not.toHaveBeenCalled();
	});
});
