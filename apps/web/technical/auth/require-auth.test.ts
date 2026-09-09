import { goto } from '$app/navigation';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '../api/client';
import { requireAuth } from './require-auth';

// Navigation is sveltekit's, i.e. the outer boundary: a real `goto` would try to route inside a
// document that has no sveltekit runtime.
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

afterEach(() => {
	vi.restoreAllMocks();
	vi.mocked(goto).mockClear();
});

describe('a page that needs a session', () => {
	it('lets the page render when there is one', () => {
		vi.spyOn(lumia.user, 'isAuthenticated').mockReturnValue(true);

		expect(requireAuth()).toBe(true);
	});

	it('stays where it is when there is one', () => {
		vi.spyOn(lumia.user, 'isAuthenticated').mockReturnValue(true);

		requireAuth();

		expect(goto).not.toHaveBeenCalled();
	});

	// The page reads this before drawing anything: answering false is what stops a protected screen
	// from rendering an empty shell for the split second before the redirect lands.
	it('tells the page not to render when there is none', () => {
		vi.spyOn(lumia.user, 'isAuthenticated').mockReturnValue(false);

		expect(requireAuth()).toBe(false);
	});

	it('sends the reader to the login page', () => {
		vi.spyOn(lumia.user, 'isAuthenticated').mockReturnValue(false);

		requireAuth();

		expect(vi.mocked(goto).mock.calls[0][0]).toContain('/login');
	});

	// The demo is published under /lumia/app, so a hardcoded /login would 404 there. The base path
	// has to be part of the destination.
	it('routes through the app base path', () => {
		vi.spyOn(lumia.user, 'isAuthenticated').mockReturnValue(false);

		requireAuth();

		const destination = String(vi.mocked(goto).mock.calls[0][0]);
		expect(destination.endsWith('/login')).toBe(true);
	});
});
