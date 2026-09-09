import { goto } from '$app/navigation';
import { render, waitFor } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import LoginPage from './+page.svelte';

// Navigation is sveltekit's, i.e. the outer boundary: a real `goto` would try to route inside a
// document that has no sveltekit runtime.
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// $app/state is read-only outside a real sveltekit request, so the query string it exposes has to
// be set up per test rather than driven through a real url.
let searchParams = new URLSearchParams();
vi.mock('$app/state', () => ({
	page: {
		get url() {
			return { searchParams };
		}
	}
}));

// The client is the app's http boundary, so it is what gets replaced.
vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: {
			login: vi.fn(),
			requestMagicLink: vi.fn(),
			verifyMagicLink: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.user);

function loginPage() {
	const { container } = render(LoginPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loginForm: () => q<HTMLFormElement>('[data-test-login-form]'),
		magicToggle: () => q<HTMLButtonElement>('[data-test-magic-toggle]')!,
		magicForm: () => q<HTMLFormElement>('[data-test-magic-form]'),
		magicSent: () => q('[data-test-magic-sent]'),
		backToPassword: () => q<HTMLButtonElement>('[data-test-back-to-password]'),
		verifyingToken: () => q('[data-test-verifying-token]'),
		email: () => q<HTMLInputElement>('#email')!,
		password: () => q<HTMLInputElement>('#password')!,
		magicEmail: () => q<HTMLInputElement>('#magic-email')!,
		error: () => q('[role="alert"]')
	};
}

beforeEach(() => {
	searchParams = new URLSearchParams();
});

afterEach(() => {
	vi.mocked(goto).mockClear();
	vi.mocked(api.login).mockReset();
	vi.mocked(api.requestMagicLink).mockReset();
	vi.mocked(api.verifyMagicLink).mockReset();
});

describe('signing in with a password', () => {
	it('sends the reader to the article list on success', async () => {
		api.login.mockResolvedValue(undefined);
		const view = loginPage();

		await fireEvent.input(view.email(), { target: { value: 'reader@example.test' } });
		await fireEvent.input(view.password(), { target: { value: 'hunter2' } });
		await fireEvent.submit(view.loginForm()!);
		await waitFor(() => expect(goto).toHaveBeenCalled());

		expect(api.login).toHaveBeenCalledWith('reader@example.test', 'hunter2');
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/articles');
	});

	it('shows an error and stays put when the credentials are refused', async () => {
		api.login.mockRejectedValue(new Error('nope'));
		const view = loginPage();

		await fireEvent.submit(view.loginForm()!);
		await waitFor(() => expect(view.error()).not.toBeNull());

		expect(goto).not.toHaveBeenCalled();
	});
});

describe('switching to the passwordless flow', () => {
	it('shows the magic-link form instead of the password form', async () => {
		const view = loginPage();

		await fireEvent.click(view.magicToggle());

		expect(view.loginForm()).toBeNull();
		expect(view.magicForm()).not.toBeNull();
	});

	it('confirms the link was requested once the address is submitted', async () => {
		api.requestMagicLink.mockResolvedValue(undefined);
		const view = loginPage();
		await fireEvent.click(view.magicToggle());

		await fireEvent.input(view.magicEmail(), { target: { value: 'reader@example.test' } });
		await fireEvent.submit(view.magicForm()!);
		await waitFor(() => expect(view.magicSent()).not.toBeNull());

		expect(api.requestMagicLink).toHaveBeenCalledWith('reader@example.test');
	});

	it('returns to the password form on request', async () => {
		const view = loginPage();
		await fireEvent.click(view.magicToggle());

		await fireEvent.click(view.backToPassword()!);

		expect(view.loginForm()).not.toBeNull();
		expect(view.magicForm()).toBeNull();
	});
});

describe('opening the page from the emailed link', () => {
	it('verifies the token and signs the reader in', async () => {
		searchParams = new URLSearchParams({ magic_token: 'the-token' });
		api.verifyMagicLink.mockResolvedValue(undefined);

		loginPage();
		await waitFor(() => expect(goto).toHaveBeenCalled());

		expect(api.verifyMagicLink).toHaveBeenCalledWith('the-token');
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/articles');
	});

	it('falls back to the password form when the token is no longer valid', async () => {
		searchParams = new URLSearchParams({ magic_token: 'stale-token' });
		api.verifyMagicLink.mockRejectedValue(new Error('expired'));

		const view = loginPage();
		await waitFor(() => expect(view.loginForm()).not.toBeNull());

		expect(goto).not.toHaveBeenCalled();
	});
});
