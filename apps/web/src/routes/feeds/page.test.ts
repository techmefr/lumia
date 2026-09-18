import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { toast } from '@lumia/ui';
import { lumia } from '$technical/api/client';
import { feed, folder } from '../test-support/fixtures';
import FeedsPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// The toast is the only place a refresh outcome is said out loud, so its wording is part of what
// this page owes the reader rather than a detail of the design system.
vi.mock('@lumia/ui', async () => {
	const actual = await vi.importActual<typeof import('@lumia/ui')>('@lumia/ui');
	return { ...actual, toast: vi.fn() };
});

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		feed: {
			listFolders: vi.fn(),
			listFeeds: vi.fn(),
			getUnreadCounts: vi.fn(),
			refreshAllFeeds: vi.fn(),
			listInstanceFeeds: vi.fn(),
			attachInstanceFeeds: vi.fn(),
			discoverFeeds: vi.fn(),
			createFolder: vi.fn(),
			renameFolder: vi.fn(),
			deleteFolder: vi.fn(),
			addFeedByUrl: vi.fn(),
			updateFeed: vi.fn(),
			deleteFeed: vi.fn(),
			refreshFeed: vi.fn(),
			importOpml: vi.fn(),
			exportOpml: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia, { deep: true });

function feedsPage() {
	const { container } = render(FeedsPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		error: () => q('[data-test-feeds-error]'),
		empty: () => q('[data-test-feeds-empty]'),
		subscribed: () => [...container.querySelectorAll('[data-test-subscribed-feed]')],
		subscribedRemove: (id: string) =>
			q<HTMLButtonElement>(`[data-test-subscribed-feed="${id}"] button`)!,
		addFeedForm: () => q<HTMLFormElement>('[data-test-add-feed-form]')!,
		addFeedError: () => q('[data-test-add-feed-error]'),
		feedUrl: () => q<HTMLInputElement>('#new-feed-url')!,
		feedFolder: () => q<HTMLSelectElement>('#new-feed-folder')!,
		newFolderForm: () => q<HTMLFormElement>('[data-test-new-folder-form]')!,
		folderName: () => q<HTMLInputElement>('#new-folder-name')!,
		opmlInput: () => q<HTMLInputElement>('[data-test-opml-input]')!,
		exportButton: () => q<HTMLButtonElement>('[data-test-id="export-opml-button"]')!,
		selectFeed: async (id: string) => {
			const selector = `[data-test-feed="${id}"]`;
			await waitFor(() => expect(q(selector)).not.toBeNull());
			await fireEvent.click(q<HTMLElement>(selector)!);
		},
		selectFolder: async (id: string) => {
			const selector = `[data-test-folder="${id}"]`;
			await waitFor(() => expect(q(selector)).not.toBeNull());
			await fireEvent.click(q<HTMLElement>(selector)!);
		},
		viewArticles: () => q<HTMLButtonElement>('[data-test-view-articles]')!,
		feedPanelRemove: () => q<HTMLButtonElement>('[data-test-feed-remove]'),
		feedRename: () => q<HTMLButtonElement>('[data-test-feed-rename]'),
		feedRenameForm: () => q<HTMLFormElement>('[data-test-feed-rename-form]'),
		feedTitle: () => q<HTMLInputElement>('#feed-title')!,
		feedFolderSelect: () => q<HTMLSelectElement>('[data-test-feed-folder]')!,
		refresh: () => q<HTMLButtonElement>('[data-test-feed-refresh]'),
		feedErrorBanner: () => q('[data-test-feed-error-banner]'),
		folderPanel: () => q('[data-test-folder-panel]'),
		refreshAll: () => q<HTMLButtonElement>('[data-test-refresh-all]')!,
		interval: () => q<HTMLSelectElement>('[data-test-feed-interval]')!,
		lastChecked: () => q('[data-test-feed-last-checked]'),
		folderDelete: () => q<HTMLButtonElement>('[data-test-folder-delete]')!
	};
}

async function withFeeds(feeds = [feed('feed-1')], folders = [folder('folder-1')]) {
	api.feed.listFeeds.mockResolvedValue(feeds);
	api.feed.listFolders.mockResolvedValue(folders);
	const view = feedsPage();
	await waitFor(() =>
		expect(feeds.length === 0 ? view.empty() !== null : view.subscribed().length > 0).toBe(true)
	);
	return view;
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.feed.listFolders.mockResolvedValue([]);
	api.feed.listFeeds.mockResolvedValue([]);
	api.feed.listInstanceFeeds.mockResolvedValue([]);
	api.feed.discoverFeeds.mockResolvedValue([]);
	api.feed.getUnreadCounts.mockResolvedValue({ total: 0, feeds: {}, folders: {} });
});

afterEach(() => {
	// `globals` is off in this project, so testing-library never registers its own cleanup and a
	// page from a previous test would keep its document and window listeners bound.
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('opening the subscriptions screen', () => {
	it('lists the feeds the reader is subscribed to', async () => {
		const view = await withFeeds([feed('feed-1'), feed('feed-2')]);

		await waitFor(() => expect(view.subscribed()).toHaveLength(2));
		expect(view.empty()).toBeNull();
	});

	it('invites the reader to subscribe when there is nothing yet', async () => {
		const view = feedsPage();

		await waitFor(() => expect(view.empty()).not.toBeNull());
	});

	it('says so when the subscriptions cannot be fetched', async () => {
		api.feed.listFeeds.mockRejectedValue(new Error('offline'));

		const view = feedsPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		feedsPage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/login');
		expect(api.feed.listFeeds).not.toHaveBeenCalled();
	});
});

describe('subscribing to a feed by url', () => {
	it('files the new feed in the chosen folder and reloads the list', async () => {
		const view = await withFeeds([], [folder('folder-1')]);
		api.feed.addFeedByUrl.mockResolvedValue(feed('feed-9'));

		await fireEvent.input(view.feedUrl(), { target: { value: 'https://example.test/rss ' } });
		await fireEvent.change(view.feedFolder(), { target: { value: 'folder-1' } });
		await fireEvent.submit(view.addFeedForm());

		await waitFor(() =>
			expect(api.feed.addFeedByUrl).toHaveBeenCalledWith('https://example.test/rss', 'folder-1')
		);
		await waitFor(() => expect(api.feed.listFeeds).toHaveBeenCalledTimes(2));
	});

	it('leaves the url in place and explains the failure when the feed is refused', async () => {
		const view = await withFeeds([]);
		api.feed.addFeedByUrl.mockRejectedValue(new Error('not a feed'));

		await fireEvent.input(view.feedUrl(), { target: { value: 'https://example.test/page' } });
		await fireEvent.submit(view.addFeedForm());

		await waitFor(() => expect(view.addFeedError()).not.toBeNull());
		expect(view.feedUrl().value).toBe('https://example.test/page');
	});

	it('asks for nothing when the url field is blank', async () => {
		const view = await withFeeds([]);

		await fireEvent.submit(view.addFeedForm());

		expect(api.feed.addFeedByUrl).not.toHaveBeenCalled();
	});
});

describe('organising feeds into folders', () => {
	it('creates a folder and clears the field afterwards', async () => {
		const view = await withFeeds([], []);
		api.feed.createFolder.mockResolvedValue(folder('folder-2', 'Lecture'));

		await fireEvent.input(view.folderName(), { target: { value: '  Lecture  ' } });
		await fireEvent.submit(view.newFolderForm());

		await waitFor(() => expect(api.feed.createFolder).toHaveBeenCalledWith('Lecture'));
		await waitFor(() => expect(view.folderName().value).toBe(''));
	});

	it('creates nothing from a name made only of spaces', async () => {
		const view = await withFeeds([], []);

		await fireEvent.input(view.folderName(), { target: { value: '   ' } });
		await fireEvent.submit(view.newFolderForm());

		expect(api.feed.createFolder).not.toHaveBeenCalled();
	});

	it('moves a feed to another folder from its panel', async () => {
		const view = await withFeeds([feed('feed-1')], [folder('folder-1')]);
		api.feed.updateFeed.mockResolvedValue(feed('feed-1', { folder_id: 'folder-1' }));

		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.feedFolderSelect()).not.toBeNull());
		await fireEvent.change(view.feedFolderSelect(), { target: { value: 'folder-1' } });

		await waitFor(() =>
			expect(api.feed.updateFeed).toHaveBeenCalledWith('feed-1', { folder_id: 'folder-1' })
		);
	});

	// Feeds outlive the folder that held them, so the panel has to survive the folder going away.
	it('deletes a folder without deleting the feeds it held', async () => {
		const view = await withFeeds([feed('feed-1', { folder_id: 'folder-1' })], [folder('folder-1')]);
		api.feed.deleteFolder.mockResolvedValue(undefined);

		await view.selectFolder('folder-1');
		await waitFor(() => expect(view.folderPanel()).not.toBeNull());
		await fireEvent.click(view.folderDelete());

		await waitFor(() => expect(api.feed.deleteFolder).toHaveBeenCalledWith('folder-1'));
		expect(api.feed.deleteFeed).not.toHaveBeenCalled();
	});
});

describe('acting on one feed', () => {
	it('opens its panel when picked in the sidebar', async () => {
		const view = await withFeeds([feed('feed-1', { title: 'Atelier Papier' })]);

		await view.selectFeed('feed-1');

		await waitFor(() => expect(view.feedPanelRemove()).not.toBeNull());
	});

	it('renames it and goes back to the read-only panel', async () => {
		const view = await withFeeds([feed('feed-1')]);
		api.feed.updateFeed.mockResolvedValue(feed('feed-1', { title: 'Nouveau titre' }));
		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.feedRename()).not.toBeNull());

		await fireEvent.click(view.feedRename()!);
		await waitFor(() => expect(view.feedRenameForm()).not.toBeNull());
		await fireEvent.input(view.feedTitle(), { target: { value: 'Nouveau titre' } });
		await fireEvent.submit(view.feedRenameForm()!);

		await waitFor(() =>
			expect(api.feed.updateFeed).toHaveBeenCalledWith('feed-1', { title: 'Nouveau titre' })
		);
		await waitFor(() => expect(view.feedRenameForm()).toBeNull());
	});

	it('unsubscribes and drops the panel it was showing', async () => {
		const view = await withFeeds([feed('feed-1')]);
		api.feed.deleteFeed.mockResolvedValue(undefined);
		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.feedPanelRemove()).not.toBeNull());
		api.feed.listFeeds.mockResolvedValue([]);

		await fireEvent.click(view.feedPanelRemove()!);

		await waitFor(() => expect(api.feed.deleteFeed).toHaveBeenCalledWith('feed-1'));
		await waitFor(() => expect(view.feedPanelRemove()).toBeNull());
	});

	it('unsubscribes from the subscription list too', async () => {
		const view = await withFeeds([feed('feed-1')]);
		api.feed.deleteFeed.mockResolvedValue(undefined);
		await waitFor(() => expect(view.subscribed()).toHaveLength(1));

		await fireEvent.click(view.subscribedRemove('feed-1'));

		await waitFor(() => expect(api.feed.deleteFeed).toHaveBeenCalledWith('feed-1'));
	});

	it('shows why a broken feed stopped updating', async () => {
		const view = await withFeeds([
			feed('feed-1', { error_reason: 'unreachable', error_since: '2026-08-01T10:00:00Z' })
		]);

		await view.selectFeed('feed-1');

		await waitFor(() => expect(view.feedErrorBanner()).not.toBeNull());
	});

	// Only Miniflux-backed feeds are polled by the instance; a manual one has nothing to re-poll.
	it('offers a re-poll only for a feed the instance polls', async () => {
		const view = await withFeeds([feed('feed-1', { source_type: 'manual' })]);

		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.feedPanelRemove()).not.toBeNull());

		expect(view.refresh()).toBeNull();
	});

	it('re-polls a miniflux feed and reloads the list', async () => {
		const view = await withFeeds([feed('feed-1')]);
		api.feed.refreshFeed.mockResolvedValue(feed('feed-1'));
		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.refresh()).not.toBeNull());

		await fireEvent.click(view.refresh()!);

		await waitFor(() => expect(api.feed.refreshFeed).toHaveBeenCalledWith('feed-1'));
		await waitFor(() => expect(api.feed.listFeeds).toHaveBeenCalledTimes(2));
	});
});

describe('moving subscriptions in and out', () => {
	it('imports an opml file and reloads the subscriptions', async () => {
		const view = await withFeeds([]);
		api.feed.importOpml.mockResolvedValue([]);
		const file = new File(['<opml />'], 'abonnements.opml', { type: 'text/xml' });

		await fireEvent.change(view.opmlInput(), { target: { files: [file] } });

		await waitFor(() => expect(api.feed.importOpml).toHaveBeenCalledWith(file));
		await waitFor(() => expect(api.feed.listFeeds).toHaveBeenCalledTimes(2));
	});

	it('reports an import that the backend refused', async () => {
		const view = await withFeeds([]);
		api.feed.importOpml.mockRejectedValue(new Error('malformed'));
		const file = new File(['nope'], 'abonnements.opml', { type: 'text/xml' });

		await fireEvent.change(view.opmlInput(), { target: { files: [file] } });

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('hands the exported file to the browser as a download', async () => {
		const view = await withFeeds([feed('feed-1')]);
		api.feed.exportOpml.mockResolvedValue(new Blob(['<opml />'], { type: 'text/xml' }));
		vi.stubGlobal('URL', { ...URL, createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() });
		const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

		await fireEvent.click(view.exportButton());

		await waitFor(() => expect(click).toHaveBeenCalled());
		click.mockRestore();
	});

	it('reports an export the backend refused', async () => {
		const view = await withFeeds([feed('feed-1')]);
		api.feed.exportOpml.mockRejectedValue(new Error('boom'));

		await fireEvent.click(view.exportButton());

		await waitFor(() => expect(view.error()).not.toBeNull());
	});
});

describe('reading what a selection holds', () => {
	it('opens the article list scoped to the selected feed', async () => {
		const view = await withFeeds([feed('feed-1')]);
		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.feedPanelRemove()).not.toBeNull());

		await fireEvent.click(view.viewArticles());

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls.at(-1)?.[0])).toContain('feed_id=feed-1');
	});
});

describe('refreshing on demand', () => {
	const REQUESTED = { feeds_requested: 3, requested_at: '2026-09-16T12:00:00Z' };

	it('offers a refresh for every feed at once', async () => {
		const view = await withFeeds();

		expect(view.refreshAll()).not.toBeNull();
	});

	it('asks the backend once when the reader refreshes everything', async () => {
		const view = await withFeeds();
		api.feed.refreshAllFeeds.mockResolvedValue(REQUESTED);

		await fireEvent.click(view.refreshAll());

		await waitFor(() => expect(api.feed.refreshAllFeeds).toHaveBeenCalledTimes(1));
	});

	it('tells the reader the articles are on their way, never that they arrived', async () => {
		const view = await withFeeds();
		api.feed.refreshAllFeeds.mockResolvedValue(REQUESTED);

		await fireEvent.click(view.refreshAll());

		await waitFor(() => expect(toast).toHaveBeenCalled());
		// The webhook delivers the entries after this resolves, so a "done" here would be a lie.
		const message = vi.mocked(toast).mock.calls[0][0] as string;
		expect(message).toMatch(/instant|shortly|moment/i);
	});

	it('reports a failure instead of pretending the refresh worked', async () => {
		const view = await withFeeds();
		api.feed.refreshAllFeeds.mockRejectedValue(new Error('boom'));

		await fireEvent.click(view.refreshAll());

		await waitFor(() =>
			expect(toast).toHaveBeenCalledWith(expect.any(String), { tone: 'destructive' })
		);
	});
});

describe('the per-feed refresh interval', () => {
	it('defaults to letting the provider choose the pace', async () => {
		const view = await withFeeds();
		await view.selectFeed('feed-1');

		await waitFor(() => expect(view.interval()).not.toBeNull());
		expect(view.interval().value).toBe('');
	});

	it('sends the chosen interval to the backend', async () => {
		const view = await withFeeds();
		api.feed.updateFeed.mockResolvedValue(feed('feed-1', { refresh_interval_minutes: 60 }));
		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.interval()).not.toBeNull());

		await fireEvent.change(view.interval(), { target: { value: '60' } });

		await waitFor(() =>
			expect(api.feed.updateFeed).toHaveBeenCalledWith('feed-1', {
				refresh_interval_minutes: 60
			})
		);
	});

	it('sends an explicit null when the reader hands the pace back', async () => {
		const view = await withFeeds([feed('feed-1', { refresh_interval_minutes: 60 })]);
		api.feed.updateFeed.mockResolvedValue(feed('feed-1', { refresh_interval_minutes: null }));
		await view.selectFeed('feed-1');
		await waitFor(() => expect(view.interval()).not.toBeNull());

		await fireEvent.change(view.interval(), { target: { value: '' } });

		await waitFor(() =>
			expect(api.feed.updateFeed).toHaveBeenCalledWith('feed-1', {
				refresh_interval_minutes: null
			})
		);
	});

	// Entries reach Lumia by webhook after a refresh returns, so an empty date beside "last checked"
	// would read as "never fetched" for a feed that was fetched a minute ago.
	it('says a feed has never been checked rather than showing an empty date', async () => {
		const view = await withFeeds();
		await view.selectFeed('feed-1');

		await waitFor(() => expect(view.lastChecked()).not.toBeNull());
		expect(view.lastChecked()?.textContent?.trim()).not.toBe('');
	});
});
