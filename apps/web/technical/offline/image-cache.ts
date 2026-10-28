export const IMAGE_CACHE_NAME = 'lumia-offline-images';
export const SYNC_IMAGES_MESSAGE = 'lumia-sync-images';

export async function syncImageCache(urls: string[]): Promise<void> {
	if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
	const registration = await navigator.serviceWorker.ready;
	registration.active?.postMessage({ type: SYNC_IMAGES_MESSAGE, urls });
}
