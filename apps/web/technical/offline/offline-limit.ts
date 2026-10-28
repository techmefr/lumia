const STORAGE_KEY = 'lumia-offline-limit';

export const OFFLINE_LIMIT_OPTIONS = [0, 25, 50, 100, 200];
export const DEFAULT_OFFLINE_LIMIT = 50;

export function getOfflineLimit(): number {
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		const stored = Number(raw);
		return raw !== null && OFFLINE_LIMIT_OPTIONS.includes(stored) ? stored : DEFAULT_OFFLINE_LIMIT;
	} catch {
		return DEFAULT_OFFLINE_LIMIT;
	}
}

export function setOfflineLimit(limit: number): void {
	try {
		localStorage.setItem(STORAGE_KEY, String(limit));
	} catch {
		return;
	}
}
