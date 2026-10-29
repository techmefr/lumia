import { IMAGE_CACHE_NAME } from './image-cache';
import { DATABASE_NAME, closeOfflineDatabase, isOfflineStorageAvailable } from './offline-db';

function deleteDatabase(): Promise<void> {
	return new Promise((resolve) => {
		const request = indexedDB.deleteDatabase(DATABASE_NAME);
		request.onsuccess = () => resolve();
		request.onerror = () => resolve();
		request.onblocked = () => resolve();
	});
}

export async function clearOfflineData(): Promise<void> {
	if (isOfflineStorageAvailable()) {
		await closeOfflineDatabase();
		await deleteDatabase();
	}
	if (typeof caches !== 'undefined') {
		await caches.delete(IMAGE_CACHE_NAME).catch(() => false);
	}
}
