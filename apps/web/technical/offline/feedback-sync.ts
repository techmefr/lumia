import { ApiError, type FeedbackUpdate } from '@lumia/core';
import { isOfflineStorageAvailable } from './offline-db';
import {
	clearPendingFeedback,
	listPendingFeedback,
	queueFeedback,
	recordFailedAttempt,
	type PendingFeedback
} from './feedback-queue';

type SendFeedback = (articleId: string, update: FeedbackUpdate) => Promise<void>;

export type DropReason = 'rejected' | 'exhausted' | 'foreign';

export type OnDropped = (articleId: string, reason: DropReason) => void;

export const MAX_ATTEMPTS = 5;

const REJECTED_FOR_GOOD = new Set([400, 403, 404, 410, 413, 422]);

function isRejectedForGood(error: unknown): boolean {
	return error instanceof ApiError && REJECTED_FOR_GOOD.has(error.status);
}

function isTransient(error: unknown): boolean {
	return (
		error instanceof ApiError &&
		(error.status >= 500 || error.status === 408 || error.status === 429)
	);
}

export function createFeedbackSync(
	send: SendFeedback,
	isOnline: () => boolean,
	getOwner: () => string | null = () => null,
	onDropped: OnDropped = () => {}
) {
	let flushing: Promise<void> | null = null;

	async function discard(pending: PendingFeedback, reason: DropReason): Promise<void> {
		await clearPendingFeedback(pending.articleId, pending.revision);
		onDropped(pending.articleId, reason);
	}

	async function replay(pending: PendingFeedback): Promise<boolean> {
		if ((pending.owner ?? null) !== getOwner()) {
			await discard(pending, 'foreign');
			return true;
		}
		try {
			await send(pending.articleId, pending.update);
		} catch (error) {
			if (isRejectedForGood(error)) {
				await discard(pending, 'rejected');
				return true;
			}
			if (!(error instanceof ApiError)) return false;
			const attempts = await recordFailedAttempt(pending.articleId, pending.revision);
			if (attempts >= MAX_ATTEMPTS) await discard(pending, 'exhausted');
			return true;
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
					if (error instanceof ApiError && !isTransient(error)) throw error;
				}
			}
		}
		await queueFeedback(articleId, update, getOwner());
	}

	return { submit, flush };
}
