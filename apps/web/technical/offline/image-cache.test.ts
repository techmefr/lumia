import { afterEach, describe, expect, it, vi } from 'vitest';
import { SYNC_IMAGES_MESSAGE, syncImageCache } from './image-cache';

afterEach(() => {
	vi.unstubAllGlobals();
	Reflect.deleteProperty(navigator, 'serviceWorker');
});

describe('syncImageCache', () => {
	it('hands the wanted addresses to the active service worker', async () => {
		const postMessage = vi.fn();
		Object.defineProperty(navigator, 'serviceWorker', {
			configurable: true,
			value: { ready: Promise.resolve({ active: { postMessage } }) }
		});

		await syncImageCache(['https://img.test/a.png']);

		expect(postMessage).toHaveBeenCalledWith({
			type: SYNC_IMAGES_MESSAGE,
			urls: ['https://img.test/a.png']
		});
	});

	it('does nothing when no worker is running yet', async () => {
		Object.defineProperty(navigator, 'serviceWorker', {
			configurable: true,
			value: { ready: Promise.resolve({ active: null }) }
		});

		await expect(syncImageCache(['https://img.test/a.png'])).resolves.toBeUndefined();
	});

	it('does nothing in a browser without service workers', async () => {
		await expect(syncImageCache(['https://img.test/a.png'])).resolves.toBeUndefined();
	});
});
