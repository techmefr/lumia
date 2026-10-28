import type { ArticleDetail } from '@lumia/core';
import {
	ARTICLES_STORE,
	openOfflineDatabase,
	requestResult,
	transactionDone
} from './offline-db';

export type ListedAs = 'saved' | 'unread';

export interface StoredArticle {
	id: string;
	article: ArticleDetail;
	listedAs: ListedAs;
}

export async function putStoredArticles(entries: StoredArticle[]): Promise<void> {
	const database = await openOfflineDatabase();
	const transaction = database.transaction(ARTICLES_STORE, 'readwrite');
	const store = transaction.objectStore(ARTICLES_STORE);
	for (const entry of entries) store.put(entry);
	await transactionDone(transaction);
}

export async function getStoredArticle(id: string): Promise<StoredArticle | null> {
	const database = await openOfflineDatabase();
	const store = database.transaction(ARTICLES_STORE).objectStore(ARTICLES_STORE);
	const entry = await requestResult<StoredArticle | undefined>(store.get(id));
	return entry ?? null;
}

export async function listStoredArticles(listedAs?: ListedAs): Promise<StoredArticle[]> {
	const database = await openOfflineDatabase();
	const store = database.transaction(ARTICLES_STORE).objectStore(ARTICLES_STORE);
	const entries = await requestResult<StoredArticle[]>(store.getAll());
	return entries
		.filter((entry) => listedAs === undefined || entry.listedAs === listedAs)
		.sort((a, b) => b.article.published_at.localeCompare(a.article.published_at));
}

export async function removeStoredArticles(ids: string[]): Promise<void> {
	const database = await openOfflineDatabase();
	const transaction = database.transaction(ARTICLES_STORE, 'readwrite');
	const store = transaction.objectStore(ARTICLES_STORE);
	for (const id of ids) store.delete(id);
	await transactionDone(transaction);
}
