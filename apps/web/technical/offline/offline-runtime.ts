import { base } from '$app/paths';
import { lumia } from '$technical/api/client';
import { OfflineLibrary } from '$domain/offline/offline-library.svelte';
import { OfflineWriteQueue } from '$domain/offline/offline-write-queue.svelte';
import { watchConnectivity } from '../network/connectivity.svelte';
import { createIndexedDbDatabase } from './offline-database';

const db = createIndexedDbDatabase();

/** One instance for the whole app: the saved list, the article page and the layout all read and
 *  write the same offline copies and the same pending-writes queue. */
export const offlineLibrary = new OfflineLibrary(db);
export const writeQueue = new OfflineWriteQueue(db);

async function flushQueue(): Promise<void> {
	await writeQueue.flush((articleId, payload) => lumia.recommendation.sendFeedback(articleId, payload));
}

/**
 * Registers the app-shell service worker and starts the reconnect flush. Owned by the root layout,
 * called once on mount. Kept out of that component so it can be reasoned about — and, if it ever
 * needs one, tested — on its own.
 */
export function startOfflineRuntime(): () => void {
	void offlineLibrary.init();
	void writeQueue.init().then(flushQueue);

	if ('serviceWorker' in navigator) {
		void navigator.serviceWorker.register(`${base}/service-worker.js`).catch(() => {
			/* offline-only browsing keeps working without the shell being precached */
		});
	}

	const stopWatching = watchConnectivity();
	window.addEventListener('online', flushQueue);
	return () => {
		stopWatching();
		window.removeEventListener('online', flushQueue);
	};
}
