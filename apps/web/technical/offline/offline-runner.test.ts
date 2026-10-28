import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '../api/client';
import { articleDetail, articleSummary } from '../../src/routes/test-support/fixtures';
import { freshOfflineDatabase } from '../../test-support/fresh-offline-database';
import { listStoredArticles } from './article-store';
import { connectivity } from './connectivity.svelte';
import { queueFeedback } from './feedback-queue';
import { runOfflineSync, startOfflineSync } from './offline-runner';

vi.mock('../api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn() },
		article: { listArticles: vi.fn(), getArticle: vi.fn() },
		recommendation: { getSaved: vi.fn(), sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

beforeEach(() => {
	freshOfflineDatabase();
	connectivity.online = true;
	api.user.isAuthenticated.mockReturnValue(true);
	api.recommendation.getSaved.mockResolvedValue([articleSummary('s1')]);
	api.article.listArticles.mockResolvedValue([articleSummary('u1')]);
	api.article.getArticle.mockImplementation(async (id: string) => articleDetail(id));
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
});

afterEach(() => {
	vi.clearAllMocks();
	connectivity.online = true;
});

describe('runOfflineSync', () => {
	it('downloads the lists within the stored cap', async () => {
		localStorage.setItem('lumia-offline-limit', '25');

		await runOfflineSync(true);

		expect((await listStoredArticles()).map((entry) => entry.id).sort()).toEqual(['s1', 'u1']);
		expect(api.article.listArticles).toHaveBeenCalledWith(
			expect.objectContaining({ unreadOnly: true })
		);
	});

	it('sends what was queued offline before it downloads anything', async () => {
		await queueFeedback('s1', { sentiment: 'like' });

		await runOfflineSync(true);

		expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('s1', { sentiment: 'like' });
	});

	it('does nothing while offline', async () => {
		connectivity.online = false;

		await runOfflineSync(true);

		expect(api.recommendation.getSaved).not.toHaveBeenCalled();
	});

	it('does nothing for a reader who is not signed in', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		await runOfflineSync(true);

		expect(api.recommendation.getSaved).not.toHaveBeenCalled();
	});

	it('does not repeat itself within a few minutes unless forced', async () => {
		await runOfflineSync(true);
		await runOfflineSync();

		expect(api.recommendation.getSaved).toHaveBeenCalledTimes(1);

		await runOfflineSync(true);

		expect(api.recommendation.getSaved).toHaveBeenCalledTimes(2);
	});

	it('shares one run between simultaneous callers', async () => {
		await Promise.all([runOfflineSync(true), runOfflineSync(true)]);

		expect(api.recommendation.getSaved).toHaveBeenCalledTimes(1);
	});

	it('swallows a failed pass, so the app never breaks on it', async () => {
		api.recommendation.getSaved.mockRejectedValue(new TypeError('Failed to fetch'));

		await expect(runOfflineSync(true)).resolves.toBeUndefined();
	});
});

describe('startOfflineSync', () => {
	it('runs again when the network comes back, and stops when torn down', async () => {
		const stop = startOfflineSync();
		await vi.waitFor(() => expect(api.recommendation.getSaved).toHaveBeenCalledTimes(1));

		window.dispatchEvent(new Event('online'));
		await vi.waitFor(() => expect(api.recommendation.getSaved).toHaveBeenCalledTimes(2));

		stop();
		window.dispatchEvent(new Event('online'));
		await new Promise((resolve) => setTimeout(resolve, 0));
		expect(api.recommendation.getSaved).toHaveBeenCalledTimes(2);
	});
});
