import { afterAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { LumiaClient } from '@lumia/core';
import { createDemoClient } from './demo-client';
import { SEED_ARTICLES, SEED_FEEDS, SEED_READ } from './seed';

vi.useFakeTimers({ shouldAdvanceTime: true, advanceTimeDelta: 5 });
afterAll(() => {
	vi.useRealTimers();
});

let demo: LumiaClient;

beforeEach(() => {
	localStorage.clear();
	demo = createDemoClient();
});

describe('the demo reading statistics', () => {
	it('answers one entry per day of the requested period', async () => {
		const stats = await demo.recommendation.getReadingStatistics(14);
		expect(stats.period_days).toBe(14);
		expect(stats.daily).toHaveLength(14);
	});

	it('counts the articles already read in the seed', async () => {
		const stats = await demo.recommendation.getReadingStatistics();
		expect(stats.articles_read).toBe(SEED_READ.length);
		expect(stats.daily.reduce((total, day) => total + day.articles_read, 0)).toBe(
			SEED_READ.length
		);
	});

	it('follows what the reader reads during the session', async () => {
		const before = await demo.recommendation.getReadingStatistics();
		const unread = SEED_ARTICLES.find((article) => !SEED_READ.includes(article.id))!;

		await demo.recommendation.sendFeedback(unread.id, { read: true });

		const after = await demo.recommendation.getReadingStatistics();
		expect(after.articles_read).toBe(before.articles_read + 1);
		expect(after.reading_minutes).toBeGreaterThan(before.reading_minutes);
	});

	it('ranks feeds, authors and keywords by what was read', async () => {
		const stats = await demo.recommendation.getReadingStatistics();
		const counts = stats.top_feeds.map((feed) => feed.articles_read);
		expect(counts).toEqual([...counts].sort((a, b) => b - a));
		expect(stats.top_authors.length).toBeGreaterThan(0);
		expect(stats.top_keywords.length).toBeGreaterThan(0);
	});

	it('lists the least read feed first with consistent counts', async () => {
		const stats = await demo.recommendation.getReadingStatistics();
		const ratios = stats.feed_engagement.map((entry) => entry.read_ratio);
		expect(ratios).toEqual([...ratios].sort((a, b) => a - b));
		for (const entry of stats.feed_engagement) {
			expect(entry.read + entry.ignored).toBe(entry.received);
		}
		expect(stats.feed_engagement.length).toBeLessThanOrEqual(SEED_FEEDS.length);
	});

	it('totals the reactions', async () => {
		const stats = await demo.recommendation.getReadingStatistics();
		expect(stats.totals.saved).toBeGreaterThan(0);
		expect(stats.totals.favorites).toBeGreaterThan(0);
		expect(stats.totals.liked).toBeGreaterThan(0);
		expect(stats.totals.disliked).toBeGreaterThan(0);
	});
});

describe('the demo popularity', () => {
	it('only lists articles at or above the reader threshold', async () => {
		const popularity = await demo.recommendation.getPopularArticles(30);
		expect(popularity.period_days).toBe(30);
		expect(popularity.articles.length).toBeGreaterThan(0);
		expect(
			popularity.articles.every((article) => article.readers >= popularity.min_readers)
		).toBe(true);
	});
});
