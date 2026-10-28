import { ApiError, type FeedbackUpdate } from '@lumia/core';
import { isOfflineStorageAvailable } from './offline-db';
import {
	clearPendingFeedback,
	listPendingFeedback,
	queueFeedback,
	type PendingFeedback
} from './feedback-queue';

type SendFeedback = (articleId: string, update: FeedbackUpdate) => Promise<void>;

function isRejectedForGood(error: unknown): boolean {
	return error instanceof ApiError && (error.status === 404 || error.status === 422);
}

export function createFeedbackSync(send: SendFeedback, isOnline: () => boolean) {
	let flushing: Promise<void> | null = null;

	async function replay(pending: PendingFeedback): Promise<boolean> {
		try {
			await send(pending.articleId, pending.update);
		} catch (error) {
			if (!isRejectedForGood(error)) return false;
		}
		await clearPendingFeedback(pending.articleId, pending.revision);
		return true;
	}

	async function drain(): Promise<void> {
		for (const pending of await listPendingFeedback()) {
			if (!(await replay(pending))) return;
		}
	}

	function flush(): Promise<void> {
		if (!isOfflineStorageAvailable() || !isOnline()) return Promise.resolve();
		flushing ??= drain().finally(() => {
			flushing = null;
		});
		return flushing;
	}

	async function submit(articleId: string, update: FeedbackUpdate): Promise<void> {
		if (!isOfflineStorageAvailable()) return send(articleId, update);
		if (isOnline()) {
			await flush().catch(() => {});
			const pending = await listPendingFeedback();
			if (!pending.some((entry) => entry.articleId === articleId)) {
				try {
					return await send(articleId, update);
				} catch (error) {
					if (error instanceof ApiError) throw error;
				}
			}
		}
		await queueFeedback(articleId, update);
	}

	return { submit, flush };
}
