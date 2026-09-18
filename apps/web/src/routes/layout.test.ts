import { createRawSnippet } from 'svelte';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import Layout from './+layout.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn(), onNavigate: vi.fn() }));

let pathname = '/articles';
vi.mock('$app/state', () => ({
	page: {
		get url() {
			return { pathname };
		}
	}
}));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { logout: vi.fn() },
		feed: { getUnreadCounts: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

function layout() {
	const { container } = render(Layout, {
		children: createRawSnippet(() => ({ render: () => '<p data-test-child>Le contenu</p>' }))
	} as never);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		child: () => q('[data-test-child]'),
		header: () => q('header'),
		skipLink: () => q('a.skip-link'),
		mobileNav: () => q('nav[class*="fixed"]'),
		main: () => q<HTMLElement>('[data-test-main]')!,
		navLink: (href: string) => q<HTMLAnchorElement>(`[data-test-nav-link="${href}"]`),
		help: () => q('[data-test-shortcuts-help]'),
		helpClose: () => q<HTMLButtonElement>('[data-test-shortcuts-help-close]')!,
		announcement: () => q('[data-test-shortcut-announcement]'),
		activeLinks: () =>
			[...container.querySelectorAll('[aria-current="page"]')].map(
				(element) => element.getAttribute('href') ?? ''
			)
	};
}

beforeEach(() => {
	pathname = '/articles';
	vi.stubGlobal(
		'matchMedia',
		vi.fn(() => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }))
	);
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			disconnect() {}
		}
	);
	api.feed.getUnreadCounts.mockResolvedValue({ total: 0, feeds: {}, folders: {} });
});

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('the app shell', () => {
	it('renders the page inside the main region', () => {
		const view = layout();

		expect(view.main().contains(view.child())).toBe(true);
	});

	it('offers the navigation and a skip link on an ordinary screen', () => {
		const view = layout();

		expect(view.header()).not.toBeNull();
		expect(view.skipLink()).not.toBeNull();
		expect(view.mobileNav()).not.toBeNull();
	});

	// Sign-in and onboarding are reachable without a session, so the chrome they would offer leads
	// nowhere; the whole screen is the form.
	it.each(['/login', '/onboarding'])('drops the chrome on %s', (route) => {
		pathname = route;
		const view = layout();

		expect(view.header()).toBeNull();
		expect(view.skipLink()).toBeNull();
		expect(view.mobileNav()).toBeNull();
		expect(view.child()).not.toBeNull();
	});
});

describe('marking where the reader is', () => {
	it('marks the section currently open', () => {
		const view = layout();

		expect(view.activeLinks()).toContain('/articles');
	});

	// A route nested under a section still belongs to it, or reading an article would leave the
	// navigation pointing at nothing.
	it('marks the section a nested route belongs to', () => {
		pathname = '/articles/article-1';
		const view = layout();

		expect(view.activeLinks()).toContain('/articles');
	});

	it('marks nothing outside the sections it lists', () => {
		pathname = '/settings';
		const view = layout();

		expect(view.activeLinks()).toHaveLength(0);
	});

	it('does not mistake one section for another that starts the same way', () => {
		pathname = '/feeds';
		const view = layout();

		expect(view.activeLinks()).not.toContain('/articles');
	});
});

describe('the width the page is given', () => {
	// An article body is a measure rather than a container; every other screen is a list or a form
	// and gets the whole display.
	it('narrows to a reading measure on an article', () => {
		pathname = '/articles/article-1';
		const view = layout();

		expect(view.main().className).toContain('max-w-reading');
	});

	it('uses the full application width everywhere else', () => {
		const view = layout();

		expect(view.main().className).toContain('max-w-app');
	});
});

describe('signing out', () => {
	it('ends the session and returns to the sign-in screen', async () => {
		api.user.logout.mockResolvedValue(undefined);
		const view = layout();
		const toggle = view.container.querySelector<HTMLButtonElement>('[data-test-menu-toggle]');

		await fireEvent.click(toggle!);
		const logout = view.container.querySelector<HTMLButtonElement>(
			'[data-test-menu-entry="Sign out"]'
		);
		await fireEvent.click(logout!);

		await waitFor(() => expect(api.user.logout).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls.at(-1)?.[0])).toContain('/login');
	});
});

describe('jumping between sections from the keyboard', () => {
	it('goes to the section the sequence names', async () => {
		layout();

		await fireEvent.keyDown(document, { key: 'g' });
		await fireEvent.keyDown(document, { key: 'f' });

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls.at(-1)?.[0])).toContain('/feeds');
	});

	// The prefix on its own is not a command: a stray `g` must leave the next keypress alone.
	it('goes nowhere on the prefix alone', async () => {
		layout();

		await fireEvent.keyDown(document, { key: 'g' });

		expect(goto).not.toHaveBeenCalled();
	});

	it('goes nowhere when the second key names no section', async () => {
		layout();

		await fireEvent.keyDown(document, { key: 'g' });
		await fireEvent.keyDown(document, { key: 'z' });

		expect(goto).not.toHaveBeenCalled();
	});

	// Jumping to the screen already open would repaint for nothing and move the focus out of
	// whatever the reader was using.
	it('stays put when the sequence names the section already open', async () => {
		layout();

		await fireEvent.keyDown(document, { key: 'g' });
		await fireEvent.keyDown(document, { key: 'a' });

		expect(goto).not.toHaveBeenCalled();
	});

	// Signing in is a dead end on purpose: a jump out of it would only meet the auth guard.
	it('refuses to jump out of the sign-in screen', async () => {
		pathname = '/login';
		layout();

		await fireEvent.keyDown(document, { key: 'g' });
		await fireEvent.keyDown(document, { key: 'f' });

		expect(goto).not.toHaveBeenCalled();
	});

	// A jump that only repaints leaves a keyboard reader where it was, so where they landed has to
	// be said out loud.
	it('announces the section it landed on', async () => {
		const view = layout();

		await fireEvent.keyDown(document, { key: 'g' });
		await fireEvent.keyDown(document, { key: 'f' });

		await waitFor(() => expect(view.announcement()?.textContent?.trim()).not.toBe(''));
	});
});

describe('the shortcut help', () => {
	it('opens on the question mark and closes again', async () => {
		const view = layout();

		await fireEvent.keyDown(document, { key: '?' });
		await waitFor(() => expect(view.help()).not.toBeNull());

		await fireEvent.click(view.helpClose());
		await waitFor(() => expect(view.help()).toBeNull());
	});

	// The help is a dialog, and a dialog owns the keyboard: the navigation sequence behind it must
	// not fire while it is up.
	it('holds the navigation sequence while it is open', async () => {
		const view = layout();
		await fireEvent.keyDown(document, { key: '?' });
		await waitFor(() => expect(view.help()).not.toBeNull());

		await fireEvent.keyDown(document, { key: 'g' });
		await fireEvent.keyDown(document, { key: 'f' });

		expect(goto).not.toHaveBeenCalled();
	});
});
