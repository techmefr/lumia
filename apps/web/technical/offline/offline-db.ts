export const DATABASE_NAME = 'lumia-offline';
const DATABASE_VERSION = 1;

export const ARTICLES_STORE = 'articles';
export const QUEUE_STORE = 'queue';

let opening: Promise<IDBDatabase> | null = null;

export function isOfflineStorageAvailable(): boolean {
	return typeof indexedDB !== 'undefined';
}

export function openOfflineDatabase(): Promise<IDBDatabase> {
	if (opening) return opening;
	opening = new Promise((resolve, reject) => {
		const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);
		request.onupgradeneeded = () => {
			const database = request.result;
			database.createObjectStore(ARTICLES_STORE, { keyPath: 'id' });
			database.createObjectStore(QUEUE_STORE, { keyPath: 'articleId' });
		};
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => {
			opening = null;
			reject(request.error);
		};
	});
	return opening;
}

export async function closeOfflineDatabase(): Promise<void> {
	const pending = opening;
	opening = null;
	if (!pending) return;
	try {
		(await pending).close();
	} catch {
		return;
	}
}

export function resetOfflineDatabaseHandle(): void {
	opening = null;
}

export function requestResult<T>(request: IDBRequest<T>): Promise<T> {
	return new Promise((resolve, reject) => {
		request.onsuccess = () => resolve(request.result);
		request.onerror = () => reject(request.error);
	});
}

export function transactionDone(transaction: IDBTransaction): Promise<void> {
	return new Promise((resolve, reject) => {
		transaction.oncomplete = () => resolve();
		transaction.onerror = () => reject(transaction.error);
		transaction.onabort = () => reject(transaction.error);
	});
}
