import type { CachedArticleRecord, OfflineDatabase, PendingWriteRecord } from './offline-database';

/**
 * An in-memory stand-in for `createIndexedDbDatabase`, used by tests. jsdom has no IndexedDB
 * implementation, and the business logic in `domain/offline` only needs the `OfflineDatabase`
 * contract — not a real browser database — to be exercised.
 */
export function createInMemoryOfflineDatabase(): OfflineDatabase {
	const articles = new Map<string, CachedArticleRecord>();
	const pendingWrites = new Map<string, PendingWriteRecord>();

	return {
		async putArticle(record) {
			articles.set(record.id, record);
		},
		async getArticle(id) {
			return articles.get(id) ?? null;
		},
		async deleteArticle(id) {
			articles.delete(id);
		},
		async listArticles() {
			return [...articles.values()];
		},
		async enqueueWrite(record) {
			pendingWrites.set(record.id, record);
		},
		async listPendingWrites() {
			return [...pendingWrites.values()];
		},
		async deletePendingWrite(id) {
			pendingWrites.delete(id);
		}
	};
}
