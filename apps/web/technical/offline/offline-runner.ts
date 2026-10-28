import { lumia } from '../api/client';
import { syncOfflineArticles } from './article-sync';
import { connectivity, watchConnectivity } from './connectivity.svelte';
import { feedbackGateway } from './feedback-gateway';
import { syncImageCache } from './image-cache';
import { isOfflineStorageAvailable } from './offline-db';
import { getOfflineLimit } from './offline-limit';

const MIN_INTERVAL_MS = 5 * 60_000;

let running: Promise<void> | null = null;
let lastCompletedAt = 0;

export function runOfflineSync(force = false): Promise<void> {
	if (!force && Date.now() - lastCompletedAt < MIN_INTERVAL_MS) return Promise.resolve();
	if (!isOfflineStorageAvailable() || !connectivity.online || !lumia.user.isAuthenticated()) {
		return Promise.resolve();
	}
	running ??= (async () => {
		await feedbackGateway.flush();
		await syncOfflineArticles(
			{
				getSaved: (limit, offset) => lumia.recommendation.getSaved(limit, offset),
				listArticles: (params) => lumia.article.listArticles(params),
				getArticle: (articleId) => lumia.article.getArticle(articleId)
			},
			getOfflineLimit(),
			syncImageCache
		);
		lastCompletedAt = Date.now();
	})()
		.catch(() => {})
		.finally(() => {
			running = null;
		});
	return running;
}

export function startOfflineSync(): () => void {
	void runOfflineSync(true);
	return watchConnectivity(() => void runOfflineSync(true));
}
