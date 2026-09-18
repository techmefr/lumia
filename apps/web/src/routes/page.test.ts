import { cleanup, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import RootPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { isAuthenticated: vi.fn() } }
}));

const api = vi.mocked(lumia.user, { deep: true });

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('landing on the app root', () => {
	it('takes a signed-in reader straight to the articles', async () => {
		api.isAuthenticated.mockReturnValue(true);

		render(RootPage);

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/articles');
	});

	it('takes everyone else to the sign-in screen', async () => {
		api.isAuthenticated.mockReturnValue(false);

		render(RootPage);

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/login');
	});
});
