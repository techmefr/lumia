import type { FeedbackUpdate } from '@lumia/core';
import {
	ARTICLES_STORE,
	QUEUE_STORE,
	openOfflineDatabase,
	requestResult,
	transactionDone
} from './offline-db';
import type { StoredArticle } from './article-store';

export interface PendingFeedback {
	articleId: string;
	update: FeedbackUpdate;
	revision: number;
	owner: string | null;
	attempts: number;
}

export function mergeFeedback(previous: FeedbackUpdate, next: FeedbackUpdate): FeedbackUpdate {
	const merged: FeedbackUpdate = { ...previous, ...next };
	if (previous.scroll_progress !== undefined && next.scroll_progress !== undefined) {
		merged.scroll_progress = Math.max(previous.scroll_progress, next.scroll_progress);
	}
	return merged;
}

export async function queueFeedback(
	articleId: string,
	update: FeedbackUpdate,
	owner: string | null = null
): Promise<void> {
	const database = await openOfflineDatabase();
	const transaction = database.transaction([QUEUE_STORE, ARTICLES_STORE], 'readwrite');
	const queue = transaction.objectStore(QUEUE_STORE);
	const articles = transaction.objectStore(ARTICLES_STORE);

	const found = await requestResult<PendingFeedback | undefined>(queue.get(articleId));
	const existing = found && (found.owner ?? null) === owner ? found : undefined;
	queue.put({
		articleId,
		update: existing ? mergeFeedback(existing.update, update) : update,
		revision: (found?.revision ?? 0) + 1,
		owner,
		attempts: 0
	} satisfies PendingFeedback);

	const stored = await requestResult<StoredArticle | undefined>(articles.get(articleId));
	if (stored) {
		const article = { ...stored.article };
		if (update.read !== undefined) article.read = update.read;
		if (update.scroll_progress !== undefined) {
			article.scroll_progress = Math.max(article.scroll_progress, update.scroll_progress);
		}
		articles.put({ ...stored, article });
	}
	await transactionDone(transaction);
}

export async function listPendingFeedback(): Promise<PendingFeedback[]> {
	const database = await openOfflineDatabase();
	const store = database.transaction(QUEUE_STORE).objectStore(QUEUE_STORE);
	return requestResult<PendingFeedback[]>(store.getAll());
}

export async function clearPendingFeedback(articleId: string, revision: number): Promise<void> {
	const database = await openOfflineDatabase();
	const transaction = database.transaction(QUEUE_STORE, 'readwrite');
	const store = transaction.objectStore(QUEUE_STORE);
	const current = await requestResult<PendingFeedback | undefined>(store.get(articleId));
	if (current && current.revision === revision) store.delete(articleId);
	await transactionDone(transaction);
}

export async function recordFailedAttempt(articleId: string, revision: number): Promise<number> {
	const database = await openOfflineDatabase();
	const transaction = database.transaction(QUEUE_STORE, 'readwrite');
	const store = transaction.objectStore(QUEUE_STORE);
	const current = await requestResult<PendingFeedback | undefined>(store.get(articleId));
	let attempts = 0;
	if (current && current.revision === revision) {
		attempts = (current.attempts ?? 0) + 1;
		store.put({ ...current, attempts });
	}
	await transactionDone(transaction);
	return attempts;
}
