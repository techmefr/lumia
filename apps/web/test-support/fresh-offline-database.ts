import { IDBFactory } from 'fake-indexeddb';
import { resetOfflineDatabaseHandle } from '../technical/offline/offline-db';

export function freshOfflineDatabase(): void {
	globalThis.indexedDB = new IDBFactory();
	resetOfflineDatabaseHandle();
}
