import type { Feed } from '@lumia/core';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { toast } from '@lumia/ui';
import FeedsPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));
vi.mock('$app/paths', () => ({ base: '' }));

vi.mock('@lumia/ui', async () => {
	const actual = await vi.importActual<typeof import('@lumia/ui')>('@lumia/ui');
	return { ...actual, toast: vi.fn() };
});

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: () => true },
		feed: {
			listFolders: vi.fn(),
			listFeeds: vi.fn(),
			getUnreadCounts: vi.fn(),
			listInstanceFeeds: vi.fn(),
			discoverFeeds: vi.fn(),
			refreshFeed: vi.fn(),
			refreshAllFeeds: vi.fn(),
			updateFeed: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia);

function feed(overrides: Partial<Feed> = {}): Feed {
	return {
		id: 'feed-1',
		folder_id: null,
		source_type: 'miniflux',
		external_feed_id: '7',
		title: 'Atelier Papier',
		url: 'https://blog.test/rss',
		error_count: 0,
		error_reason: null,
		error_since: null,
		refresh_interval_minutes: null,
		last_refreshed_at: null,
		...overrides
	};
}

beforeEach(() => {
	vi.clearAllMocks();
	vi.mocked(api.feed.listFolders).mockResolvedValue([]);
	vi.mocked(api.feed.listFeeds).mockResolvedValue([feed()]);
	vi.mocked(api.feed.getUnreadCounts).mockResolvedValue({ total: 0, feeds: {}, folders: {} });
	vi.mocked(api.feed.listInstanceFeeds).mockResolvedValue([]);
	vi.mocked(api.feed.discoverFeeds).mockResolvedValue([]);
});

async function page() {
	const { container } = render(FeedsPage);
	await waitFor(() => expect(vi.mocked(api.feed.listFeeds)).toHaveBeenCalled());
	return {
		container,
		refreshAll: () => container.querySelector('[data-test-refresh-all]') as HTMLButtonElement,
		selectFeed: async () => {
			// The sidebar renders its rows through an animated list, so the row appears a tick after
			// the feeds resolve rather than in the same frame.
			const row = await waitFor(() => {
				const found = container.querySelector('[data-test-feed="feed-1"]');
				if (!found) throw new Error('feed row not rendered yet');
				return found as HTMLElement;
			});
			await fireEvent.click(row);
		},
		interval: () => container.querySelector('[data-test-feed-interval]') as HTMLSelectElement,
		lastChecked: () => container.querySelector('[data-test-feed-last-checked]')
	};
}

describe('refreshing on demand', () => {
	it('offers a refresh for every feed at once', async () => {
		const view = await page();
		expect(view.refreshAll()).not.toBeNull();
	});

	it('asks the backend once when the reader refreshes everything', async () => {
		vi.mocked(api.feed.refreshAllFeeds).mockResolvedValue({
			feeds_requested: 3,
			requested_at: '2026-09-16T12:00:00Z'
		});
		const view = await page();

		await fireEvent.click(view.refreshAll());

		await waitFor(() => expect(vi.mocked(api.feed.refreshAllFeeds)).toHaveBeenCalledTimes(1));
	});

	it('tells the reader the articles are on their way, never that they arrived', async () => {
		vi.mocked(api.feed.refreshAllFeeds).mockResolvedValue({
			feeds_requested: 3,
			requested_at: '2026-09-16T12:00:00Z'
		});
		const view = await page();

		await fireEvent.click(view.refreshAll());

		await waitFor(() => expect(toast).toHaveBeenCalled());
		// The webhook delivers the entries after this resolves, so a "done" here would be a lie.
		const message = vi.mocked(toast).mock.calls[0][0] as string;
		expect(message).toMatch(/instant|shortly|moment/i);
	});

	it('reports a failure instead of pretending the refresh worked', async () => {
		vi.mocked(api.feed.refreshAllFeeds).mockRejectedValue(new Error('boom'));
		const view = await page();

		await fireEvent.click(view.refreshAll());

		await waitFor(() =>
			expect(toast).toHaveBeenCalledWith(expect.any(String), { tone: 'destructive' })
		);
	});
});

describe('the per-feed interval', () => {
	it('defaults to letting the provider choose the pace', async () => {
		const view = await page();
		await view.selectFeed();

		expect(view.interval().value).toBe('');
	});

	it('sends the chosen interval to the backend', async () => {
		vi.mocked(api.feed.updateFeed).mockResolvedValue(feed({ refresh_interval_minutes: 60 }));
		const view = await page();
		await view.selectFeed();

		await fireEvent.change(view.interval(), { target: { value: '60' } });

		await waitFor(() =>
			expect(vi.mocked(api.feed.updateFeed)).toHaveBeenCalledWith('feed-1', {
				refresh_interval_minutes: 60
			})
		);
	});

	it('sends an explicit null when the reader hands the pace back', async () => {
		vi.mocked(api.feed.listFeeds).mockResolvedValue([feed({ refresh_interval_minutes: 60 })]);
		vi.mocked(api.feed.updateFeed).mockResolvedValue(feed({ refresh_interval_minutes: null }));
		const view = await page();
		await view.selectFeed();

		await fireEvent.change(view.interval(), { target: { value: '' } });

		await waitFor(() =>
			expect(vi.mocked(api.feed.updateFeed)).toHaveBeenCalledWith('feed-1', {
				refresh_interval_minutes: null
			})
		);
	});

	it('says a feed has never been checked rather than showing an empty date', async () => {
		const view = await page();
		await view.selectFeed();

		expect(view.lastChecked()?.textContent?.trim()).not.toBe('');
	});
});
