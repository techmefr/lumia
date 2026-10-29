import { afterEach, describe, expect, it, vi } from 'vitest';
import {
	MAX_SYNCED_IMAGES,
	SYNC_IMAGES_MESSAGE,
	acceptedImageUrls,
	isTrustedSource,
	syncImageCache
} from './image-cache';

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

describe('image address filter', () => {
	it('keeps http and https addresses once each', () => {
		expect(
			acceptedImageUrls(['https://a.test/1.png', 'http://a.test/2.png', 'https://a.test/1.png'])
		).toEqual(['https://a.test/1.png', 'http://a.test/2.png']);
	});

	it('drops other schemes, credentials, garbage and non strings', () => {
		expect(
			acceptedImageUrls([
				'javascript:alert(1)',
				'data:image/png;base64,AA',
				'file:///etc/passwd',
				'chrome-extension://x/y',
				'https://user:pw@a.test/1.png',
				'not a url',
				42,
				null
			])
		).toEqual([]);
	});

	it('caps how many addresses one message can queue', () => {
		const many = Array.from({ length: MAX_SYNCED_IMAGES + 20 }, (_, i) => `https://a.test/${i}.png`);
		expect(acceptedImageUrls(many)).toHaveLength(MAX_SYNCED_IMAGES);
	});
});

describe('isTrustedSource', () => {
	it('accepts a client of the same origin only', () => {
		expect(isTrustedSource({ url: 'https://app.test/articles' }, 'https://app.test')).toBe(true);
		expect(isTrustedSource({ url: 'https://evil.test/' }, 'https://app.test')).toBe(false);
		expect(isTrustedSource({ url: 'nope' }, 'https://app.test')).toBe(false);
		expect(isTrustedSource({}, 'https://app.test')).toBe(false);
		expect(isTrustedSource(null, 'https://app.test')).toBe(false);
	});
});
