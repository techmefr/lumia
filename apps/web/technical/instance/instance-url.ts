const STORAGE_KEY = 'lumia-instance-url';

export function normalizeInstanceUrl(raw: string): string | null {
	const trimmed = raw.trim();
	if (!trimmed) return null;
	let url: URL;
	try {
		url = new URL(trimmed);
	} catch {
		return null;
	}
	if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
	return `${url.origin}${url.pathname.replace(/\/+$/, '')}`;
}

export function getStoredInstanceUrl(storage: Pick<Storage, 'getItem'> | undefined): string | null {
	try {
		return storage?.getItem(STORAGE_KEY) ?? null;
	} catch {
		return null;
	}
}

export function storeInstanceUrl(storage: Pick<Storage, 'setItem'>, url: string): void {
	try {
		storage.setItem(STORAGE_KEY, url);
	} catch {
		return;
	}
}

export function resolveApiBaseUrl(
	buildTimeUrl: string | undefined,
	storage: Pick<Storage, 'getItem'> | undefined
): string {
	return getStoredInstanceUrl(storage) ?? buildTimeUrl ?? '';
}
