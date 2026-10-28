import { ApiError } from '@lumia/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { articleDetail, articleSummary } from '../../src/routes/test-support/fixtures';
import { freshOfflineDatabase } from '../../test-support/fresh-offline-database';
import { putStoredArticles } from './article-store';
import { readArticle, readSavedList } from './offline-reads';

const NETWORK_DOWN = new TypeError('Failed to fetch');

beforeEach(freshOfflineDatabase);

describe('readArticle', () => {
	it('returns what the server says when it answers', async () => {
		const article = articleDetail('a1', { title: 'En ligne' });

		expect(await readArticle(async () => article, 'a1')).toBe(article);
	});

	it('falls back to the stored copy when the network is down', async () => {
		await putStoredArticles([
			{ id: 'a1', article: articleDetail('a1', { title: 'Stocké' }), listedAs: 'saved' }
		]);

		const article = await readArticle(() => Promise.reject(NETWORK_DOWN), 'a1');

		expect(article.title).toBe('Stocké');
	});

	it('fails with the original error for an article that was never downloaded', async () => {
		await expect(readArticle(() => Promise.reject(NETWORK_DOWN), 'a1')).rejects.toBe(NETWORK_DOWN);
	});

	it('does not hide a server answer behind a stale copy', async () => {
		await putStoredArticles([{ id: 'a1', article: articleDetail('a1'), listedAs: 'saved' }]);
		const refusal = new ApiError(404, {});

		await expect(readArticle(() => Promise.reject(refusal), 'a1')).rejects.toBe(refusal);
	});

	it('rethrows when the browser has no storage to fall back on', async () => {
		vi.stubGlobal('indexedDB', undefined);

		await expect(readArticle(() => Promise.reject(NETWORK_DOWN), 'a1')).rejects.toBe(NETWORK_DOWN);
		vi.unstubAllGlobals();
	});
});

describe('readSavedList', () => {
	it('returns the live list, not flagged offline', async () => {
		const listing = await readSavedList(async () => [articleSummary('s1')]);

		expect(listing.offline).toBe(false);
		expect(listing.articles.map((a) => a.id)).toEqual(['s1']);
	});

	it('serves only the stored reading list, newest first, when the network is down', async () => {
		await putStoredArticles([
			{
				id: 's-old',
				article: articleDetail('s-old', { published_at: '2026-01-01T00:00:00Z' }),
				listedAs: 'saved'
			},
			{
				id: 's-new',
				article: articleDetail('s-new', { published_at: '2026-06-01T00:00:00Z' }),
				listedAs: 'saved'
			},
			{ id: 'u1', article: articleDetail('u1'), listedAs: 'unread' }
		]);

		const listing = await readSavedList(() => Promise.reject(NETWORK_DOWN));

		expect(listing.offline).toBe(true);
		expect(listing.articles.map((a) => a.id)).toEqual(['s-new', 's-old']);
	});

	it('reports the failure when nothing was ever downloaded', async () => {
		await expect(readSavedList(() => Promise.reject(NETWORK_DOWN))).rejects.toBe(NETWORK_DOWN);
	});

	it('does not replace a server error with a stored list', async () => {
		await putStoredArticles([{ id: 's1', article: articleDetail('s1'), listedAs: 'saved' }]);
		const failure = new ApiError(500, {});

		await expect(readSavedList(() => Promise.reject(failure))).rejects.toBe(failure);
	});
});
