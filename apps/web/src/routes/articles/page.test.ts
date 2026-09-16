import { cleanup, render, waitFor } from '@testing-library/svelte';
import { fireEvent } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { toasts } from '@lumia/ui';
import { lumia } from '$technical/api/client';
import { setShortcutsEnabled } from '$technical/keyboard/shortcuts-store.svelte.js';
import { articleSummary as article, feed, folder } from '../test-support/fixtures';
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
		recommendation: { markRead: vi.fn(), sendFeedback: vi.fn(), bulkFeedback: vi.fn() },
		playlist: { listPlaylists: vi.fn(), bulkSetItems: vi.fn() }
	}
}));

const api = vi.mocked(lumia);

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
			[...container.querySelectorAll<HTMLButtonElement>('[data-test-display-mode] button')][1],
		error: () => q('[data-test-articles-error]'),
		cards: () => [...container.querySelectorAll('[data-test-article-card]')],
		card: (id: string) => q(`[data-test-article-card="${id}"]`),
		unreadOnly: () => q<HTMLButtonElement>('[data-test-unread-only]')!,
		markAllRead: () => q<HTMLButtonElement>('[data-test-mark-all-read]')!,
		clearTagFilter: () => q<HTMLButtonElement>('[data-test-clear-tag-filter]'),
		loadMore: () => q<HTMLButtonElement>('[data-test-load-more]'),
		selectFeed: async (id: string) => {
			const selector = `[data-test-feed="${id}"]`;
			await waitFor(() => expect(q(selector)).not.toBeNull());
			await fireEvent.click(q<HTMLElement>(selector)!);
		},
		selectionToggle: () => q<HTMLButtonElement>('[data-test-selection-toggle]'),
		selectionBar: () => q('[data-test-selection-bar]'),
		selectionCount: () => q('[data-test-selection-count]'),
		checkbox: (id: string) => q<HTMLInputElement>(`[data-test-select-article="${id}"]`),
		bulkMarkRead: () => q<HTMLButtonElement>('[data-test-selection-read]'),
		bulkSave: () => q<HTMLButtonElement>('[data-test-selection-save]')
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
	vi.mocked(api.playlist.listPlaylists).mockResolvedValue([]);
	vi.mocked(api.recommendation.bulkFeedback).mockResolvedValue({
		updated: 1,
		changed_article_ids: ['a']
	});
	toasts.toasts = [];
});

afterEach(() => {
	// `globals` is off in this project, so testing-library never registers its own cleanup: without
	// this, a page from a previous test keeps its document-level shortcut listener bound.
	cleanup();
	setShortcutsEnabled(true);
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


/** The parameters the list was last asked for, which is the page's observable output. */
function lastRequest(): Record<string, unknown> {
	return vi.mocked(api.article.listArticles).mock.calls.at(-1)?.[0] as Record<string, unknown>;
}

describe('loading the list', () => {
	beforeEach(() => stubViewport(false));

	it('says so when the list cannot be fetched', async () => {
		vi.mocked(api.article.listArticles).mockRejectedValue(new Error('offline'));
		const view = articlesPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('picks up the feed and folder scope carried by the url', async () => {
		stubUrl = new URL('http://test/articles?feed_id=feed-3');
		articlesPage();

		await waitFor(() => expect(api.article.listArticles).toHaveBeenCalled());
		expect(lastRequest().feedId).toBe('feed-3');
	});

	it('picks up a keyword filter and drops it when the chip is dismissed', async () => {
		stubUrl = new URL('http://test/articles?keyword_id=kw-1&keyword_term=typographie');
		const view = articlesPage();
		await waitFor(() => expect(view.clearTagFilter()).not.toBeNull());
		expect(lastRequest().keywordId).toBe('kw-1');

		await fireEvent.click(view.clearTagFilter()!);

		await waitFor(() => expect(lastRequest().keywordId).toBeUndefined());
		expect(view.clearTagFilter()).toBeNull();
	});

	// The counts are decoration; a list that vanished because a badge failed would be a worse bug
	// than a missing badge.
	it('still shows the articles when the unread counts fail', async () => {
		vi.mocked(api.feed.getUnreadCounts).mockRejectedValue(new Error('nope'));
		const view = articlesPage();

		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));
		expect(view.error()).toBeNull();
	});

	it('offers more only once a full page came back', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		expect(view.loadMore()).toBeNull();
	});

	it('appends the next page after the ones already on screen', async () => {
		const firstPage = Array.from({ length: 24 }, (_, index) => article(`a${index}`));
		vi.mocked(api.article.listArticles).mockResolvedValue(firstPage);
		const view = articlesPage();
		await waitFor(() => expect(view.loadMore()).not.toBeNull());
		vi.mocked(api.article.listArticles).mockResolvedValue([article('later')]);

		await fireEvent.click(view.loadMore()!);

		await waitFor(() => expect(view.card('later')).not.toBeNull());
		expect(lastRequest().offset).toBe(24);
		expect(view.cards()).toHaveLength(25);
	});
});

describe('narrowing the list to what is unread', () => {
	beforeEach(() => stubViewport(false));

	it('asks for unread articles only, then for everything again', async () => {
		const view = articlesPage();
		await waitFor(() => expect(api.article.listArticles).toHaveBeenCalled());

		await fireEvent.click(view.unreadOnly());
		await waitFor(() => expect(lastRequest().unreadOnly).toBe(true));

		await fireEvent.click(view.unreadOnly());
		await waitFor(() => expect(lastRequest().unreadOnly).toBeUndefined());
	});

	it('toggles through the u shortcut as well', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'u' });

		await waitFor(() => expect(lastRequest().unreadOnly).toBe(true));
	});
});

describe('marking a scope as read', () => {
	beforeEach(() => {
		stubViewport(false);
		vi.mocked(api.recommendation.markRead).mockResolvedValue({ updated: 2 });
	});

	it('marks everything when no feed or folder is selected', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.click(view.markAllRead());

		await waitFor(() => expect(api.recommendation.markRead).toHaveBeenCalledWith({ all: true }));
	});

	it('scopes the request to the selected feed', async () => {
		vi.mocked(api.feed.listFeeds).mockResolvedValue([feed('feed-1')]);
		vi.mocked(api.feed.listFolders).mockResolvedValue([folder('folder-1')]);
		const view = articlesPage();
		await view.selectFeed('feed-1');

		await fireEvent.click(view.markAllRead());

		await waitFor(() =>
			expect(api.recommendation.markRead).toHaveBeenCalledWith({ feed_id: 'feed-1' })
		);
	});

	// "Tout" is the one scope with no ceiling, so a large one asks before wiping the backlog.
	it('asks before clearing a large unread backlog', async () => {
		vi.mocked(api.feed.getUnreadCounts).mockResolvedValue({ total: 300, feeds: {}, folders: {} });
		const confirm = vi.fn(() => false);
		vi.stubGlobal('confirm', confirm);
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.click(view.markAllRead());

		expect(confirm).toHaveBeenCalled();
		expect(api.recommendation.markRead).not.toHaveBeenCalled();
	});

	it('asks nothing for a handful of unread articles', async () => {
		vi.mocked(api.feed.getUnreadCounts).mockResolvedValue({ total: 3, feeds: {}, folders: {} });
		const confirm = vi.fn(() => true);
		vi.stubGlobal('confirm', confirm);
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.click(view.markAllRead());

		await waitFor(() => expect(api.recommendation.markRead).toHaveBeenCalled());
		expect(confirm).not.toHaveBeenCalled();
	});
});

describe('driving the list from the keyboard', () => {
	beforeEach(() => stubViewport(false));

	it('opens the article the cursor sits on', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'j' });
		await fireEvent.keyDown(document, { key: 'o' });

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls.at(-1)?.[0])).toContain('/articles/a');
	});

	it('walks down then back up without running off the top', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'j' });
		await fireEvent.keyDown(document, { key: 'j' });
		await fireEvent.keyDown(document, { key: 'k' });
		await fireEvent.keyDown(document, { key: 'k' });
		await fireEvent.keyDown(document, { key: 'k' });
		await fireEvent.keyDown(document, { key: 'o' });

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls.at(-1)?.[0])).toContain('/articles/a');
	});

	it('flips the read state of the article under the cursor', async () => {
		vi.mocked(api.recommendation.sendFeedback).mockResolvedValue(undefined);
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'j' });
		await fireEvent.keyDown(document, { key: 'm' });

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { read: true })
		);
		await waitFor(() => expect(view.card('a')?.getAttribute('data-test-read')).toBe('true'));
	});

	it('saves the article under the cursor', async () => {
		vi.mocked(api.recommendation.sendFeedback).mockResolvedValue(undefined);
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'j' });
		await fireEvent.keyDown(document, { key: 's' });

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { saved: true })
		);
	});

	it('does nothing while the cursor sits on no article', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'm' });
		await fireEvent.keyDown(document, { key: 's' });
		await fireEvent.keyDown(document, { key: 'o' });

		expect(api.recommendation.sendFeedback).not.toHaveBeenCalled();
		expect(goto).not.toHaveBeenCalled();
	});

	// Typing a search term must not be read as a stream of commands.
	it('ignores a shortcut key typed into the search field', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.searchInput()).not.toBeNull());

		await fireEvent.keyDown(view.searchInput() as HTMLInputElement, { key: 'u' });

		expect(lastRequest().unreadOnly).toBeUndefined();
	});

	// A dialog or a menu owns the keyboard while it is up: a stray `u` behind an open overlay would
	// reorder the list the reader cannot even see.
	it.each(['dialog', 'menu'])('stands down while a %s is open', async (role) => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));
		const overlay = document.createElement('div');
		overlay.setAttribute('role', role);
		document.body.append(overlay);

		await fireEvent.keyDown(document, { key: 'u' });

		expect(lastRequest().unreadOnly).toBeUndefined();
		overlay.remove();
	});

	// WCAG 2.1.4: the reader can silence single-key shortcuts from the settings, and the list has to
	// honour that too.
	it('does nothing once the reader has turned the shortcuts off', async () => {
		setShortcutsEnabled(false);
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'u' });

		expect(lastRequest().unreadOnly).toBeUndefined();
	});

	it('puts the focus in the search field on slash', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.searchInput()).not.toBeNull());

		await fireEvent.keyDown(document, { key: '/' });

		expect(document.activeElement).toBe(view.searchInput());
	});

	it('opens the flip reader on f', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.cards().length).toBeGreaterThan(0));

		await fireEvent.keyDown(document, { key: 'f' });

		await waitFor(() => expect(view.container.querySelector('[data-test-flip-stage]')).not.toBeNull());
	});
});

describe('an empty list', () => {
	beforeEach(() => {
		stubViewport(false);
		vi.mocked(api.article.listArticles).mockResolvedValue([]);
	});

	it('points a reader with no feeds at the subscriptions screen', async () => {
		const view = articlesPage();

		await waitFor(() =>
			expect(view.container.querySelector('a[href$="/feeds"]')).not.toBeNull()
		);
		expect(view.cards()).toHaveLength(0);
	});

	it('offers a way back out of an empty search', async () => {
		const view = articlesPage();
		await waitFor(() => expect(view.searchInput()).not.toBeNull());
		await fireEvent.input(view.searchInput() as HTMLInputElement, { target: { value: 'rien' } });
		await fireEvent.click(view.searchSubmit() as HTMLButtonElement);

		await waitFor(() => expect(view.searchClear()).not.toBeNull());
		await fireEvent.click(view.searchClear() as HTMLButtonElement);

		await waitFor(() => expect(lastRequest().query).toBeUndefined());
	});
});

describe('acting on a selection of articles', () => {
	beforeEach(() => stubViewport(false));

	async function withSelection() {
		const view = articlesPage();
		await waitFor(() => expect(view.selectionToggle()).not.toBeNull());
		await fireEvent.click(view.selectionToggle() as HTMLButtonElement);
		await waitFor(() => expect(view.checkbox('a')).not.toBeNull());
		await fireEvent.click(view.checkbox('a') as HTMLInputElement);
		await waitFor(() => expect(view.selectionCount()?.textContent?.trim()).toBe(
			'1 article(s) selected'
		));
		return view;
	}

	// At rest the list carries no checkbox and no bar: the feature costs nothing to a reader who
	// never uses it.
	it('shows neither the bar nor the checkboxes until selection mode is on', async () => {
		const view = articlesPage();
		await waitFor(() => expect(api.article.listArticles).toHaveBeenCalled());

		expect(view.selectionBar()).toBeNull();
		expect(view.checkbox('a')).toBeNull();
	});

	it('counts what is selected out loud', async () => {
		const view = await withSelection();
		await fireEvent.click(view.checkbox('b') as HTMLInputElement);

		await waitFor(() =>
			expect(view.selectionCount()?.textContent?.trim()).toBe('2 article(s) selected')
		);
	});

	// The endpoint takes exactly one scope. Sending the ids and only the ids is what keeps a filter
	// left on screen from widening the action to a feed, or to the whole library.
	it('sends the selected ids as the only scope of the action', async () => {
		const view = await withSelection();

		await fireEvent.click(view.bulkMarkRead() as HTMLButtonElement);

		await waitFor(() => expect(api.recommendation.bulkFeedback).toHaveBeenCalled());
		expect(api.recommendation.bulkFeedback).toHaveBeenCalledWith({
			article_ids: ['a'],
			axis: 'read',
			value: true
		});
	});

	it('touches one axis per action, never the others', async () => {
		const view = await withSelection();

		await fireEvent.click(view.bulkSave() as HTMLButtonElement);

		await waitFor(() => expect(api.recommendation.bulkFeedback).toHaveBeenCalled());
		expect(api.recommendation.bulkFeedback).toHaveBeenCalledWith({
			article_ids: ['a'],
			axis: 'saved',
			value: true
		});
	});

	it('offers an undo that puts back exactly what the backend says it changed', async () => {
		vi.mocked(api.recommendation.bulkFeedback).mockResolvedValue({
			updated: 2,
			changed_article_ids: ['b']
		});
		const view = await withSelection();
		await fireEvent.click(view.bulkMarkRead() as HTMLButtonElement);
		await waitFor(() => expect(toasts.toasts.at(-1)?.action).toBeDefined());

		await toasts.toasts.at(-1)?.action?.run();

		expect(api.recommendation.bulkFeedback).toHaveBeenLastCalledWith({
			article_ids: ['b'],
			axis: 'read',
			value: false
		});
	});

	it('says the action failed and offers no undo when the call did not go through', async () => {
		vi.mocked(api.recommendation.bulkFeedback).mockRejectedValue(new Error('down'));
		const view = await withSelection();

		await fireEvent.click(view.bulkMarkRead() as HTMLButtonElement);

		await waitFor(() => expect(toasts.toasts.at(-1)?.tone).toBe('destructive'));
		expect(toasts.toasts.at(-1)?.action).toBeUndefined();
	});

	// A selection that silently survived a change of feed or search would arm a bulk action on
	// articles the reader never saw.
	it('empties the selection when the list is reloaded under a new search', async () => {
		const view = await withSelection();

		await fireEvent.input(view.searchInput() as HTMLInputElement, {
			target: { value: 'kubernetes' }
		});
		await fireEvent.click(view.searchSubmit() as HTMLButtonElement);

		await waitFor(() =>
			expect(view.selectionCount()?.textContent?.trim()).toBe('No article selected')
		);
	});
});
