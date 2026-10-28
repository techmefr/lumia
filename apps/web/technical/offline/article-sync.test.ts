import type { ArticleDetail, ArticleSummary, ListArticlesParams } from '@lumia/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { articleDetail, articleSummary } from '../../src/routes/test-support/fixtures';
import { freshOfflineDatabase } from '../../test-support/fresh-offline-database';
import { listStoredArticles } from './article-store';
import { syncOfflineArticles, type ArticleSyncApi } from './article-sync';
import { queueFeedback } from './feedback-queue';

interface Server {
	saved: ArticleSummary[];
	unread: ArticleSummary[];
	details: Map<string, ArticleDetail>;
}

function apiFor(server: Server) {
	const getArticle = vi.fn(async (id: string) => {
		const detail = server.details.get(id);
		if (!detail) throw new Error(`no article ${id}`);
		return detail;
	});
	const listArticles = vi.fn(async (params: ListArticlesParams) =>
		server.unread.slice(0, params.limit)
	);
	const getSaved = vi.fn(async (limit: number, offset: number) =>
		server.saved.slice(offset, offset + limit)
	);
	const api: ArticleSyncApi = { getSaved, listArticles, getArticle };
	return { api, getArticle, listArticles, getSaved };
}

function server(savedIds: string[], unreadIds: string[]): Server {
	const everything = [...savedIds, ...unreadIds];
	return {
		saved: savedIds.map((id) => articleSummary(id)),
		unread: unreadIds.map((id) => articleSummary(id)),
		details: new Map(everything.map((id) => [id, articleDetail(id)]))
	};
}

const noImages = async () => {};

beforeEach(freshOfflineDatabase);

describe('syncOfflineArticles', () => {
	it('stores the reading list and the unread articles, bodies included', async () => {
		const { api } = apiFor(server(['s1', 's2'], ['u1']));

		const result = await syncOfflineArticles(api, 50, noImages);

		expect(result).toEqual({ stored: 3, removed: 0 });
		const stored = await listStoredArticles();
		expect(stored.map((entry) => [entry.id, entry.listedAs]).sort()).toEqual([
			['s1', 'saved'],
			['s2', 'saved'],
			['u1', 'unread']
		]);
		expect(stored[0].article.content).toContain('corps');
	});

	it('serves the reading list first when the cap cannot hold everything', async () => {
		const { api } = apiFor(server(['s1', 's2'], ['u1', 'u2', 'u3']));

		await syncOfflineArticles(api, 3, noImages);

		const stored = await listStoredArticles();
		expect(stored.map((entry) => entry.id).sort()).toEqual(['s1', 's2', 'u1']);
	});

	it('stops inside the reading list when the cap is smaller than it', async () => {
		const { api } = apiFor(server(['s1', 's2', 's3'], ['u1']));

		await syncOfflineArticles(api, 2, noImages);

		expect((await listStoredArticles()).map((entry) => entry.id).sort()).toEqual(['s1', 's2']);
	});

	it('does not list an unread article twice when it is also in the reading list', async () => {
		const { api } = apiFor(server(['s1'], ['s1', 'u1']));

		await syncOfflineArticles(api, 10, noImages);

		const stored = await listStoredArticles();
		expect(stored.map((entry) => [entry.id, entry.listedAs]).sort()).toEqual([
			['s1', 'saved'],
			['u1', 'unread']
		]);
	});

	it('pages through a reading list longer than one request', async () => {
		const ids = Array.from({ length: 120 }, (_, index) => `s${index}`);
		const { api, getSaved } = apiFor(server(ids, []));

		await syncOfflineArticles(api, 200, noImages);

		expect(getSaved.mock.calls.length).toBeGreaterThan(1);
		expect(await listStoredArticles()).toHaveLength(120);
	});

	it('drops what left the lists, so the store never outgrows the cap', async () => {
		const first = server(['s1'], ['u1', 'u2']);
		await syncOfflineArticles(apiFor(first).api, 10, noImages);

		const result = await syncOfflineArticles(apiFor(server(['s1'], ['u2'])).api, 10, noImages);

		expect(result.removed).toBe(1);
		expect((await listStoredArticles()).map((entry) => entry.id).sort()).toEqual(['s1', 'u2']);
	});

	it('does not download a body it already holds', async () => {
		const data = server(['s1'], []);
		await syncOfflineArticles(apiFor(data).api, 10, noImages);
		const again = apiFor(data);

		await syncOfflineArticles(again.api, 10, noImages);

		expect(again.getArticle).not.toHaveBeenCalled();
	});

	it('takes the server read state for a stored article, unless the reader changed it offline', async () => {
		const data = server(['s1', 's2'], []);
		await syncOfflineArticles(apiFor(data).api, 10, noImages);
		await queueFeedback('s2', { read: true, scroll_progress: 0.7 });
		data.saved = [
			articleSummary('s1', { read: true, scroll_progress: 1 }),
			articleSummary('s2', { read: false, scroll_progress: 0 })
		];

		await syncOfflineArticles(apiFor(data).api, 10, noImages);

		const byId = new Map((await listStoredArticles()).map((entry) => [entry.id, entry.article]));
		expect(byId.get('s1')).toMatchObject({ read: true, scroll_progress: 1 });
		expect(byId.get('s2')).toMatchObject({ read: true, scroll_progress: 0.7 });
	});

	it('hands every image of every stored article to the image cache, once', async () => {
		const data = server(['s1', 's2'], []);
		data.details.set(
			's1',
			articleDetail('s1', {
				image_url: 'https://img.test/cover.jpg',
				content: '<p><img src="https://img.test/a.png"><img src="https://img.test/cover.jpg"></p>'
			})
		);
		data.details.set(
			's2',
			articleDetail('s2', { content: '<img src="/relative.png"><img src="https://img.test/b.png">' })
		);
		const syncImages = vi.fn(async () => {});

		await syncOfflineArticles(apiFor(data).api, 10, syncImages);

		expect(new Set(syncImages.mock.calls[0][0])).toEqual(
			new Set(['https://img.test/cover.jpg', 'https://img.test/a.png', 'https://img.test/b.png'])
		);
	});

	it('empties the store and the image cache when the cap is zero, without calling the server', async () => {
		await syncOfflineArticles(apiFor(server(['s1'], ['u1'])).api, 10, noImages);
		const untouched = apiFor(server(['s1'], ['u1']));
		const syncImages = vi.fn(async () => {});

		const result = await syncOfflineArticles(untouched.api, 0, syncImages);

		expect(result).toEqual({ stored: 0, removed: 2 });
		expect(await listStoredArticles()).toEqual([]);
		expect(syncImages).toHaveBeenCalledWith([]);
		expect(untouched.getSaved).not.toHaveBeenCalled();
		expect(untouched.listArticles).not.toHaveBeenCalled();
	});

	it('leaves the store as it was when a download fails midway', async () => {
		await syncOfflineArticles(apiFor(server(['s1'], [])).api, 10, noImages);
		const broken = server(['s1', 's2'], []);
		broken.details.delete('s2');

		await expect(syncOfflineArticles(apiFor(broken).api, 10, noImages)).rejects.toThrow();

		expect((await listStoredArticles()).map((entry) => entry.id)).toEqual(['s1']);
	});
});
