import type { Popularity, ReadingStatistics } from '@lumia/core';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import StatisticsPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		recommendation: { getReadingStatistics: vi.fn(), getPopularArticles: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

function statistics(overrides: Partial<ReadingStatistics> = {}): ReadingStatistics {
	return {
		period_days: 30,
		articles_read: 12,
		reading_minutes: 48,
		daily: [{ day: '2026-10-21', articles_read: 12, reading_minutes: 48 }],
		top_feeds: [{ id: 'feed-1', name: 'Fibre', articles_read: 7 }],
		top_authors: [],
		top_keywords: [{ term: 'python', articles_read: 5 }],
		feed_engagement: [
			{ feed_id: 'feed-1', title: 'Fibre', received: 10, read: 7, ignored: 3, read_ratio: 0.7 }
		],
		totals: { saved: 3, favorites: 2, liked: 1, disliked: 0 },
		...overrides
	};
}

function popularity(overrides: Partial<Popularity> = {}): Popularity {
	return {
		period_days: 7,
		min_readers: 3,
		articles: [{ title: 'Shared', url: 'https://example.test/shared', readers: 5 }],
		...overrides
	};
}

function statisticsPage() {
	const { container } = render(StatisticsPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		error: () => q('[role="alert"]'),
		articlesRead: () => q('[data-test-articles-read]')?.textContent?.trim(),
		readingTime: () => q('[data-test-reading-time]')?.textContent?.trim(),
		saved: () => q('[data-test-saved]')?.textContent?.trim(),
		favorites: () => q('[data-test-favorites]')?.textContent?.trim(),
		period: (days: number) => q<HTMLButtonElement>(`[data-test-period="${days}"]`)!,
		popular: () => [...container.querySelectorAll('[data-test-popular-article]')],
		popularEmpty: () => q('[data-test-popularity-empty]'),
		ranked: (id: string) => q(`[data-test-ranked="${id}"]`)
	};
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.recommendation.getReadingStatistics.mockResolvedValue(statistics());
	api.recommendation.getPopularArticles.mockResolvedValue(popularity());
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('the statistics page', () => {
	it('asks for the last 30 days of reading and of popularity first', async () => {
		statisticsPage();
		await waitFor(() => expect(api.recommendation.getReadingStatistics).toHaveBeenCalledWith(30));
		expect(api.recommendation.getPopularArticles).toHaveBeenCalledWith(30);
	});

	it('shows the headline figures', async () => {
		const view = statisticsPage();
		await waitFor(() => expect(view.articlesRead()).toBe('12'));
		expect(view.readingTime()).toContain('48');
		expect(view.saved()).toBe('3');
		expect(view.favorites()).toBe('2');
	});

	it('shows the rankings', async () => {
		const view = statisticsPage();
		await waitFor(() => expect(view.ranked('feeds')!.textContent).toContain('Fibre'));
		expect(view.ranked('keywords')!.textContent).toContain('python');
	});

	it('reloads for the period the reader picks and marks it pressed', async () => {
		const view = statisticsPage();
		await waitFor(() => expect(view.articlesRead()).toBe('12'));

		await fireEvent.click(view.period(90));

		await waitFor(() => expect(api.recommendation.getReadingStatistics).toHaveBeenCalledWith(90));
		expect(view.period(90).getAttribute('aria-pressed')).toBe('true');
		expect(view.period(30).getAttribute('aria-pressed')).toBe('false');
	});

	it('does not reload when the current period is picked again', async () => {
		const view = statisticsPage();
		await waitFor(() => expect(view.articlesRead()).toBe('12'));

		await fireEvent.click(view.period(30));

		expect(api.recommendation.getReadingStatistics).toHaveBeenCalledTimes(1);
	});

	it('lists the popular articles with their reader count', async () => {
		const view = statisticsPage();
		await waitFor(() => expect(view.popular()).toHaveLength(1));
		expect(view.popular()[0].textContent).toContain('Shared');
		expect(view.popular()[0].textContent).toContain('5');
	});

	it('explains that popularity is empty below the threshold', async () => {
		api.recommendation.getPopularArticles.mockResolvedValue(popularity({ articles: [] }));
		const view = statisticsPage();
		await waitFor(() => expect(view.popularEmpty()).not.toBeNull());
	});

	it('announces a failed load', async () => {
		api.recommendation.getReadingStatistics.mockRejectedValue(new Error('boom'));
		const view = statisticsPage();
		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('does not load anything while signed out', async () => {
		api.user.isAuthenticated.mockReturnValue(false);
		statisticsPage();
		await Promise.resolve();
		expect(api.recommendation.getReadingStatistics).not.toHaveBeenCalled();
	});
});
