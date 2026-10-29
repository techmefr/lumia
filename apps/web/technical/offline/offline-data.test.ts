import { beforeEach, describe, expect, it, vi } from 'vitest';
import { freshOfflineDatabase } from '../../test-support/fresh-offline-database';
import { putStoredArticles, listStoredArticles } from './article-store';
import { articleDetail } from '../../src/routes/test-support/fixtures';
import { listPendingFeedback, queueFeedback } from './feedback-queue';
import { IMAGE_CACHE_NAME } from './image-cache';
import { clearOfflineData } from './offline-data';

beforeEach(freshOfflineDatabase);

describe('clearOfflineData', () => {
	it('empties the downloaded articles and the write queue', async () => {
		await putStoredArticles([{ id: 'a1', article: articleDetail('a1'), listedAs: 'saved' }]);
		await queueFeedback('a1', { read: true });

		await clearOfflineData();

		expect(await listStoredArticles()).toEqual([]);
		expect(await listPendingFeedback()).toEqual([]);
	});

	it('deletes the image cache', async () => {
		const remove = vi.fn(async () => true);
		vi.stubGlobal('caches', { delete: remove });

		await clearOfflineData();
		vi.unstubAllGlobals();

		expect(remove).toHaveBeenCalledWith(IMAGE_CACHE_NAME);
	});

	it('still resolves when the cache api refuses', async () => {
		vi.stubGlobal('caches', { delete: vi.fn(async () => Promise.reject(new Error('no'))) });

		await expect(clearOfflineData()).resolves.toBeUndefined();
		vi.unstubAllGlobals();
	});
});
