import type { FeedbackUpdate } from '@lumia/core';

/** A cached article, already stripped down to what offline reading needs. */
export interface CachedArticleRecord {
	id: string;
	title: string;
	sourceLabel: string;
	/** Sanitized, image-free HTML — see `sanitizeArticleHtmlForOffline`. */
	content: string;
	imageUrl: string | null;
	readingMinutes: number;
	savedAt: number;
	/** UTF-16 byte length of `content`, used to enforce the storage cap without re-measuring. */
	bytes: number;
}

/** One feedback write made while offline, waiting to be replayed once the network is back. */
export interface PendingWriteRecord {
	id: string;
	articleId: string;
	payload: FeedbackUpdate;
	createdAt: number;
}

/**
 * The storage surface the offline feature needs. Kept narrow and interface-shaped so the business
 * logic in `domain/offline` can be unit-tested against an in-memory double instead of a real
 * IndexedDB, which jsdom does not implement.
 */
export interface OfflineDatabase {
	putArticle(record: CachedArticleRecord): Promise<void>;
	getArticle(id: string): Promise<CachedArticleRecord | null>;
	deleteArticle(id: string): Promise<void>;
	listArticles(): Promise<CachedArticleRecord[]>;
	enqueueWrite(record: PendingWriteRecord): Promise<void>;
	listPendingWrites(): Promise<PendingWriteRecord[]>;
	deletePendingWrite(id: string): Promise<void>;
}

const DB_NAME = 'lumia-offline';
const DB_VERSION = 1;
const ARTICLES_STORE = 'articles';
const PENDING_WRITES_STORE = 'pendingWrites';

function openDatabase(): Promise<IDBDatabase> {
	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);
		request.onupgradeneeded = () => {
			const db = request.result;
			if (!db.objectStoreNames.contains(ARTICLES_STORE)) {
				db.createObjectStore(ARTICLES_STORE, { keyPath: 'id' });
			}
			if (!db.objectStoreNames.contains(PENDING_WRITES_STORE)) {
				db.createObjectStore(PENDING_WRITES_STORE, { keyPath: 'id' });
			}
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}

function requestToPromise<T>(request: IDBRequest<T>): Promise<T> {
	return new Promise((resolve, reject) => {
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}

/**
 * The real, browser-backed implementation. Left thin and untested on purpose — like the service
 * worker it backs, IndexedDB plumbing is not meaningfully unit-testable, so the rules that matter
 * (the storage cap, opt-in, write coalescing) live in `domain/offline` instead, against this
 * interface.
 */
export function createIndexedDbDatabase(): OfflineDatabase {
	let dbPromise: Promise<IDBDatabase> | null = null;

	function db(): Promise<IDBDatabase> {
		if (!dbPromise) dbPromise = openDatabase();
		return dbPromise;
	}

	async function withStore<T>(
		storeName: string,
		mode: IDBTransactionMode,
		run: (store: IDBObjectStore) => IDBRequest<T>
	): Promise<T> {
		const database = await db();
		const transaction = database.transaction(storeName, mode);
		const store = transaction.objectStore(storeName);
		return requestToPromise(run(store));
	}

	return {
		async putArticle(record) {
			await withStore(ARTICLES_STORE, 'readwrite', (store) => store.put(record));
		},
		async getArticle(id) {
			const record = await withStore<CachedArticleRecord | undefined>(ARTICLES_STORE, 'readonly', (store) =>
				store.get(id)
			);
			return record ?? null;
		},
		async deleteArticle(id) {
			await withStore(ARTICLES_STORE, 'readwrite', (store) => store.delete(id));
		},
		async listArticles() {
			return withStore<CachedArticleRecord[]>(ARTICLES_STORE, 'readonly', (store) => store.getAll());
		},
		async enqueueWrite(record) {
			await withStore(PENDING_WRITES_STORE, 'readwrite', (store) => store.put(record));
		},
		async listPendingWrites() {
			return withStore<PendingWriteRecord[]>(PENDING_WRITES_STORE, 'readonly', (store) => store.getAll());
		},
		async deletePendingWrite(id) {
			await withStore(PENDING_WRITES_STORE, 'readwrite', (store) => store.delete(id));
		}
	};
}
