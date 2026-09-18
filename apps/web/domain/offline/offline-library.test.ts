import { describe, expect, it } from 'vitest';
import type { ArticleDetail, ArticleSummary } from '@lumia/core';
import { createInMemoryOfflineDatabase } from '$technical/offline/in-memory-offline-database';
import { DEFAULT_OFFLINE_CAP_BYTES, OfflineLibrary, OfflineQuotaExceededError } from './offline-library.svelte';

function detail(id: string, overrides: Partial<ArticleDetail> = {}): ArticleDetail {
	return {
		id,
		feed_id: 'feed-1',
		author_id: null,
		author_name: null,
		category_id: null,
		category_name: null,
		source_label: 'Atelier Papier',
		title: `Titre ${id}`,
		url: `https://example.test/${id}`,
		summary: null,
		image_url: 'https://example.test/hero.jpg',
		published_at: '2026-08-09T08:30:00Z',
		reading_minutes: 4,
		read: false,
		scroll_progress: 0,
		relevance_score: 50,
		content: '<p>Un corps d’article.</p>',
		keywords: [],
		...overrides
	};
}

function summary(id: string): ArticleSummary {
	const { content: _content, keywords: _keywords, ...rest } = detail(id);
	return rest;
}

describe('OfflineLibrary', () => {
	it('starts empty', () => {
		const library = new OfflineLibrary(createInMemoryOfflineDatabase());
		expect(library.offlineIds).toEqual([]);
		expect(library.bytesUsed).toBe(0);
	});

	it('loads whatever the database already holds on init', async () => {
		const db = createInMemoryOfflineDatabase();
		await db.putArticle({
			id: 'a1',
			title: 'A1',
			sourceLabel: 'Source',
			content: '<p>a1</p>',
			imageUrl: null,
			readingMinutes: 2,
			savedAt: Date.now(),
			bytes: 9
		});
		const library = new OfflineLibrary(db);
		await library.init();
		expect(library.isOffline('a1')).toBe(true);
		expect(library.bytesUsed).toBe(9);
	});

	it('stores an article stripped of its images, so the byte count reflects text only', async () => {
		const library = new OfflineLibrary(createInMemoryOfflineDatabase());
		await library.makeAvailable(detail('a1', { content: '<p>x</p><img src="y.jpg">' }));
		expect(library.isOffline('a1')).toBe(true);
		const stored = await library.getContent('a1');
		expect(stored?.content).not.toContain('<img');
	});

	it('does nothing on a second call for an article already offline', async () => {
		const library = new OfflineLibrary(createInMemoryOfflineDatabase());
		await library.makeAvailable(detail('a1'));
		await library.makeAvailable(detail('a1'));
		expect(library.records).toHaveLength(1);
	});

	it('removes an article and frees its bytes', async () => {
		const library = new OfflineLibrary(createInMemoryOfflineDatabase());
		await library.makeAvailable(detail('a1'));
		expect(library.bytesUsed).toBeGreaterThan(0);
		await library.makeUnavailable('a1');
		expect(library.isOffline('a1')).toBe(false);
		expect(library.bytesUsed).toBe(0);
	});

	it('refuses an article that would cross the storage cap, and leaves nothing stored', async () => {
		const library = new OfflineLibrary(createInMemoryOfflineDatabase(), 10);
		await expect(library.makeAvailable(detail('a1', { content: '<p>this is longer than ten bytes</p>' }))).rejects.toThrow(
			OfflineQuotaExceededError
		);
		expect(library.isOffline('a1')).toBe(false);
	});

	it('defaults the cap to a generous text-only budget', () => {
		const library = new OfflineLibrary(createInMemoryOfflineDatabase());
		expect(library.capBytes).toBe(DEFAULT_OFFLINE_CAP_BYTES);
	});

	describe('makeAllAvailable', () => {
		it('caches every summary given, in order, via the injected fetcher', async () => {
			const library = new OfflineLibrary(createInMemoryOfflineDatabase());
			const summaries = [summary('a1'), summary('a2')];
			const result = await library.makeAllAvailable(summaries, async (id) => detail(id));
			expect(result).toEqual({ cached: ['a1', 'a2'], skipped: [] });
			expect(library.offlineIds).toEqual(['a1', 'a2']);
		});

		it('skips what no longer fits once the cap is hit, and reports the rest as skipped too', async () => {
			const library = new OfflineLibrary(createInMemoryOfflineDatabase(), 20);
			const summaries = [summary('a1'), summary('a2'), summary('a3')];
			const result = await library.makeAllAvailable(summaries, async (id) =>
				detail(id, { content: '<p>0123456789</p>' })
			);
			expect(result.cached).toEqual(['a1']);
			expect(result.skipped).toEqual(['a2', 'a3']);
		});

		it('counts an article already offline as cached rather than re-fetching it', async () => {
			const library = new OfflineLibrary(createInMemoryOfflineDatabase());
			await library.makeAvailable(detail('a1'));
			let fetchCount = 0;
			const result = await library.makeAllAvailable([summary('a1')], async (id) => {
				fetchCount += 1;
				return detail(id);
			});
			expect(result).toEqual({ cached: ['a1'], skipped: [] });
			expect(fetchCount).toBe(0);
		});
	});
});
