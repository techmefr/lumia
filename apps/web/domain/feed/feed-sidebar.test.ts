import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import type { Feed, Folder } from '@lumia/core';
import FeedSidebar from './feed-sidebar.svelte';

type Props = Parameters<typeof FeedSidebar>[1];

const TECH: Folder = { id: 'folder-tech', name: 'Tech' };
const NEWS_FEED: Feed = {
	id: 'feed-news',
	folder_id: 'folder-tech',
	source_type: 'miniflux',
	external_feed_id: '1',
	title: 'Hacker News',
	url: 'https://news.example.com/rss'
};
const BLOG_FEED: Feed = {
	id: 'feed-blog',
	folder_id: null,
	source_type: 'miniflux',
	external_feed_id: '2',
	title: 'A personal blog',
	url: 'https://blog.example.com/rss'
};

function sidebar(overrides: Partial<Props> = {}) {
	const onSelectAll = vi.fn();
	const onSelectFolder = vi.fn();
	const onSelectFeed = vi.fn();
	const onMarkFeedRead = vi.fn();
	const onMarkFolderRead = vi.fn();
	const { container } = render(FeedSidebar, {
		folders: [TECH],
		feeds: [NEWS_FEED, BLOG_FEED],
		selectedFolderId: '',
		selectedFeedId: '',
		onSelectAll,
		onSelectFolder,
		onSelectFeed,
		onMarkFeedRead,
		onMarkFolderRead,
		...overrides
	} as Props);

	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		onSelectAll,
		onSelectFolder,
		onSelectFeed,
		onMarkFeedRead,
		onMarkFolderRead,
		selectAll: () => q<HTMLButtonElement>('[data-test-select-all]')!,
		mobileToggle: () => q<HTMLButtonElement>('[data-test-sidebar-mobile-toggle]')!,
		nav: () => q('#feed-nav')!,
		folder: (id: string) => q<HTMLButtonElement>(`[data-test-folder="${id}"]`)!,
		folderToggle: (id: string) => q<HTMLButtonElement>(`[data-test-folder-toggle="${id}"]`)!,
		folderMarkRead: (id: string) => q<HTMLButtonElement>(`[data-test-folder-mark-read="${id}"]`),
		feed: (id: string) => q<HTMLButtonElement>(`[data-test-feed="${id}"]`)!,
		feedMarkRead: (id: string) => q<HTMLButtonElement>(`[data-test-feed-mark-read="${id}"]`),
		feedError: (id: string) => q<HTMLSpanElement>(`[data-test-feed-error="${id}"]`),
		playlistsLink: () => q<HTMLAnchorElement>('[data-test-nav-playlists]')!,
		favoritesLink: () => q<HTMLAnchorElement>('[data-test-nav-favorites]')!
	};
}

describe('picking what to read', () => {
	it('lets a click select all articles', async () => {
		const view = sidebar();

		await fireEvent.click(view.selectAll());

		expect(view.onSelectAll).toHaveBeenCalledOnce();
	});

	it('marks all articles active when no folder or feed is selected', () => {
		const view = sidebar({ selectedFolderId: '', selectedFeedId: '' });
		expect(view.selectAll().className).toContain('bg-primary');
	});

	it('lets a click select a folder', async () => {
		const view = sidebar();

		await fireEvent.click(view.folder(TECH.id));

		expect(view.onSelectFolder).toHaveBeenCalledWith(TECH.id);
	});

	it('marks the selected folder current', () => {
		const view = sidebar({ selectedFolderId: TECH.id });
		expect(view.folder(TECH.id).getAttribute('aria-current')).toBe('true');
		expect(view.selectAll().className).not.toContain('bg-primary');
	});

	it('lets a click select a feed inside a folder', async () => {
		const view = sidebar();

		await fireEvent.click(view.feed(NEWS_FEED.id));

		expect(view.onSelectFeed).toHaveBeenCalledWith(NEWS_FEED.id);
	});

	it('lets a click select an unfiled feed', async () => {
		const view = sidebar();

		await fireEvent.click(view.feed(BLOG_FEED.id));

		expect(view.onSelectFeed).toHaveBeenCalledWith(BLOG_FEED.id);
	});

	it('marks the selected feed current', () => {
		const view = sidebar({ selectedFeedId: NEWS_FEED.id });
		expect(view.feed(NEWS_FEED.id).getAttribute('aria-current')).toBe('true');
	});
});

describe('unread counts', () => {
	it('shows the total next to select all', () => {
		const view = sidebar({ unread: { total: 12, feeds: {}, folders: {} } });
		expect(view.selectAll().textContent).toContain('12');
	});

	it('shows nothing when the total is zero', () => {
		const view = sidebar({ unread: { total: 0, feeds: {}, folders: {} } });
		expect(view.selectAll().textContent?.trim()).not.toMatch(/\d/);
	});

	it('shows the per-folder and per-feed counts', () => {
		const view = sidebar({
			unread: { total: 7, feeds: { [NEWS_FEED.id]: 3 }, folders: { [TECH.id]: 5 } }
		});
		expect(view.folder(TECH.id).textContent).toContain('5');
		expect(view.feed(NEWS_FEED.id).textContent).toContain('3');
	});
});

describe('marking a feed or a folder read', () => {
	it('offers no button when there is nothing unread', () => {
		const view = sidebar({ unread: { total: 0, feeds: {}, folders: {} } });
		expect(view.folderMarkRead(TECH.id)).toBeNull();
		expect(view.feedMarkRead(NEWS_FEED.id)).toBeNull();
	});

	it('offers no button when the caller does not handle it', () => {
		const view = sidebar({
			unread: { total: 5, feeds: { [NEWS_FEED.id]: 5 }, folders: { [TECH.id]: 5 } },
			onMarkFeedRead: undefined,
			onMarkFolderRead: undefined
		});
		expect(view.folderMarkRead(TECH.id)).toBeNull();
		expect(view.feedMarkRead(NEWS_FEED.id)).toBeNull();
	});

	it('marks a folder read without selecting it', async () => {
		const view = sidebar({ unread: { total: 5, feeds: {}, folders: { [TECH.id]: 5 } } });

		await fireEvent.click(view.folderMarkRead(TECH.id)!);

		expect(view.onMarkFolderRead).toHaveBeenCalledWith(TECH.id);
		expect(view.onSelectFolder).not.toHaveBeenCalled();
	});

	it('marks a feed read without selecting it', async () => {
		const view = sidebar({ unread: { total: 3, feeds: { [NEWS_FEED.id]: 3 }, folders: {} } });

		await fireEvent.click(view.feedMarkRead(NEWS_FEED.id)!);

		expect(view.onMarkFeedRead).toHaveBeenCalledWith(NEWS_FEED.id);
		expect(view.onSelectFeed).not.toHaveBeenCalled();
	});
});

describe('collapsing a folder', () => {
	it('shows its feeds by default', () => {
		const view = sidebar();
		expect(view.feed(NEWS_FEED.id)).not.toBeNull();
	});

	it('hides them once collapsed, and brings them back', async () => {
		const view = sidebar();

		await fireEvent.click(view.folderToggle(TECH.id));
		expect(view.feed(NEWS_FEED.id)).toBeNull();

		await fireEvent.click(view.folderToggle(TECH.id));
		expect(view.feed(NEWS_FEED.id)).not.toBeNull();
	});
});

describe('the mobile nav toggle', () => {
	it('starts closed', () => {
		const view = sidebar();
		expect(view.mobileToggle().getAttribute('aria-expanded')).toBe('false');
		expect(view.nav().className).toContain('hidden');
	});

	it('opens the nav on click', async () => {
		const view = sidebar();

		await fireEvent.click(view.mobileToggle());

		expect(view.mobileToggle().getAttribute('aria-expanded')).toBe('true');
		expect(view.nav().className).not.toContain('hidden');
	});
});

describe('a feed in error', () => {
	const BROKEN_FEED: Feed = {
		...BLOG_FEED,
		id: 'feed-broken',
		error_count: 4,
		error_reason: 'not_found',
		error_since: '2026-08-01T10:00:00Z'
	};

	it('shows no error indicator for a healthy feed', () => {
		const view = sidebar();
		expect(view.feedError(NEWS_FEED.id)).toBeNull();
	});

	it('shows an error indicator for a feed miniflux reports as broken', () => {
		const view = sidebar({ feeds: [NEWS_FEED, BROKEN_FEED] });
		expect(view.feedError(BROKEN_FEED.id)).not.toBeNull();
	});

	it('names the reason and the date in the tooltip, never the raw provider text', () => {
		const view = sidebar({ feeds: [NEWS_FEED, BROKEN_FEED] });
		const label = view.feedError(BROKEN_FEED.id)!.getAttribute('aria-label')!;
		expect(label).toMatch(/2026/);
		expect(label.toLowerCase()).not.toContain('miniflux');
	});
});

describe('the shortcuts at the bottom', () => {
	it('link to the playlists and the favorites', () => {
		const view = sidebar();
		expect(view.playlistsLink().getAttribute('href')).toBe('/playlists');
		expect(view.favoritesLink().getAttribute('href')).toBe('/favoris');
	});
});
