export const IMAGE_CACHE_NAME = 'lumia-offline-images';
export const SYNC_IMAGES_MESSAGE = 'lumia-sync-images';

export async function syncImageCache(urls: string[]): Promise<void> {
	if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
	const registration = await navigator.serviceWorker.ready;
	registration.active?.postMessage({ type: SYNC_IMAGES_MESSAGE, urls });
}

export const MAX_SYNCED_IMAGES = 500;

export function isCacheableImageUrl(value: unknown): value is string {
	if (typeof value !== 'string') return false;
	let url: URL;
	try {
		url = new URL(value);
	} catch {
		return false;
	}
	return (
		(url.protocol === 'https:' || url.protocol === 'http:') &&
		url.username === '' &&
		url.password === ''
	);
}

export function acceptedImageUrls(urls: unknown[]): string[] {
	return [...new Set(urls.filter(isCacheableImageUrl))].slice(0, MAX_SYNCED_IMAGES);
}

export function isTrustedSource(source: { url?: unknown } | null, origin: string): boolean {
	if (!source || typeof source.url !== 'string') return false;
	try {
		return new URL(source.url).origin === origin;
	} catch {
		return false;
	}
}
