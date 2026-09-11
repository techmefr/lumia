import type { ArticleSummary } from '@lumia/core';
import { render, waitFor } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import ArticlesPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

let stubUrl = new URL('http://test/articles');

vi.mock('$app/state', () => ({
	page: {
		get url() {
			return stubUrl;
		}
	}
}));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: () => true },
		article: { listArticles: vi.fn() },
		feed: { listFolders: vi.fn(), listFeeds: vi.fn(), getUnreadCounts: vi.fn() },
		recommendation: { markRead: vi.fn(), sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia);

function article(id: string): ArticleSummary {
	return {
		id,
		title: `Titre ${id}`,
		summary: null,
		url: `https://example.test/${id}`,
		image_url: null,
		source_label: 'Atelier Papier',
		feed_id: 'feed-1',
		published_at: '2026-08-09T08:30:00Z',
		reading_minutes: 4,
		read: false,
		scroll_progress: 0,
		relevance_score: 50,
		author_id: null,
		author_name: null,
		category_id: null,
		category_name: null
	} as ArticleSummary;
}

const crossThreshold = new Set<() => void>();
let compactWidth = false;

function stubViewport(compact: boolean) {
	compactWidth = compact;
	vi.stubGlobal(
		'matchMedia',
		vi.fn(() => ({
			get matches() {
				return compactWidth;
			},
			addEventListener: (_type: string, handler: () => void) => crossThreshold.add(handler),
			removeEventListener: (_type: string, handler: () => void) => crossThreshold.delete(handler)
		}))
	);
}

async function resizeTo(compact: boolean) {
	compactWidth = compact;
	for (const handler of crossThreshold) handler();
	await Promise.resolve();
}

function articlesPage() {
	const { container } = render(ArticlesPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		displayMode: () => q('[data-test-display-mode]'),
		flip: () => q<HTMLButtonElement>('[data-test-flip]'),
		hero: () => q('[data-test-article-hero]'),
		searchInput: () => q<HTMLInputElement>('[data-test-search-input]'),
		searchSubmit: () => q<HTMLButtonElement>('[data-test-search-submit]'),
		searchClear: () => q<HTMLButtonElement>('[data-test-search-clear]'),
		searchStatus: () => q('[data-test-search-status]'),
		kioskButton: () =>
			[...container.querySelectorAll<HTMLButtonElement>('[data-test-display-mode] button')][1]
	};
}

/** The `sort` the list was last asked for, which is what tells desktop and mobile modes apart. */
function lastRequestedSort(): string | undefined {
	const calls = vi.mocked(api.article.listArticles).mock.calls;
	return (calls.at(-1)?.[0] as { sort?: string } | undefined)?.sort;
}

beforeEach(() => {
	stubUrl = new URL('http://test/articles');
	crossThreshold.clear();
	vi.mocked(api.article.listArticles).mockResolvedValue([article('a'), article('b')]);
	vi.mocked(api.feed.listFolders).mockResolvedValue([]);
	vi.mocked(api.feed.listFeeds).mockResolvedValue([]);
	vi.mocked(api.feed.getUnreadCounts).mockResolvedValue({ total: 0, feeds: {}, folders: {} });
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('choosing a display mode on a wide screen', () => {
	beforeEach(() => stubViewport(false));

	it('offers the mode selector', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.displayMode()).not.toBeNull());
	});

	it('switches the list to the kiosque layout', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.kioskButton()).toBeDefined());

		await fireEvent.click(view.kioskButton());
		await waitFor(() => expect(view.hero()).not.toBeNull());

		expect(lastRequestedSort()).toBe('relevance');
	});
});

describe('opening the list on a narrow screen', () => {
	beforeEach(() => stubViewport(true));

	// Both modes render the same single column there, so the choice changes nothing on screen while
	// still costing a row of chrome.
	it('hides the mode selector', async () => {
		const view = articlesPage();
		await waitFor(() => expect(api.article.listArticles).toHaveBeenCalled());

		expect(view.displayMode()).toBeNull();
	});

	// The flip reader is an action, not a mode: it opens a reader and comes back, so it stays.
	it('keeps the flip reader available', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.flip()).not.toBeNull());
	});
});

describe('carrying a mode over from a wide screen', () => {
	it('drops back to the single mobile mode once the grid is one column', async () => {
		stubViewport(false);
		const view = articlesPage();
		await waitFor(() => expect(view.kioskButton()).toBeDefined());
		await fireEvent.click(view.kioskButton());
		await waitFor(() => expect(view.hero()).not.toBeNull());

		await resizeTo(true);

		await waitFor(() => expect(view.hero()).toBeNull());
		expect(view.displayMode()).toBeNull();
		// Not just the layout: leaving the list sorted by relevance with no visible control would
		// strand the reader in an order they cannot see or undo.
		await waitFor(() => expect(lastRequestedSort()).toBe('recent'));
	});
});

describe('searching articles', () => {
	beforeEach(() => stubViewport(false));

	it('has an accessible label on the search field', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.searchInput()).not.toBeNull());

		const inputId = view.searchInput()?.id;
		const label = view.container.querySelector(`label[for="${inputId}"]`);
		expect(label?.textContent).toBe('Search for an article');
	});

	it('requests the list with the submitted text and puts it in the url', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.searchInput()).not.toBeNull());

		await fireEvent.input(view.searchInput() as HTMLInputElement, {
			target: { value: 'kubernetes' }
		});
		await fireEvent.click(view.searchSubmit() as HTMLButtonElement);

		await waitFor(() => {
			const calls = vi.mocked(api.article.listArticles).mock.calls;
			expect((calls.at(-1)?.[0] as { query?: string }).query).toBe('kubernetes');
		});
		const gotoCall = vi.mocked(goto).mock.calls.at(-1);
		expect((gotoCall?.[0] as URL).searchParams.get('q')).toBe('kubernetes');
	});

	it('announces the result count through a live region', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.searchInput()).not.toBeNull());

		await fireEvent.input(view.searchInput() as HTMLInputElement, {
			target: { value: 'kubernetes' }
		});
		await fireEvent.click(view.searchSubmit() as HTMLButtonElement);

		await waitFor(() => expect(view.searchStatus()).not.toBeNull());
		expect(view.searchStatus()?.getAttribute('aria-live')).toBe('polite');
	});

	it('clears the query from the url when the search is cleared', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.searchInput()).not.toBeNull());

		await fireEvent.input(view.searchInput() as HTMLInputElement, {
			target: { value: 'kubernetes' }
		});
		await fireEvent.click(view.searchSubmit() as HTMLButtonElement);
		await waitFor(() => expect(view.searchClear()).not.toBeNull());

		await fireEvent.click(view.searchClear() as HTMLButtonElement);

		const gotoCall = vi.mocked(goto).mock.calls.at(-1);
		expect((gotoCall?.[0] as URL).searchParams.has('q')).toBe(false);
	});

	it('restores the query already carried by the url on mount', async () => {
		stubUrl = new URL('http://test/articles?q=borrow');
		const view = articlesPage();

		await waitFor(() => {
			const calls = vi.mocked(api.article.listArticles).mock.calls;
			expect((calls.at(0)?.[0] as { query?: string }).query).toBe('borrow');
		});
		expect(view.searchInput()?.value).toBe('borrow');
	});
});
