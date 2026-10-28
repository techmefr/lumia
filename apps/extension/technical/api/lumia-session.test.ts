import { afterEach, describe, expect, it, vi } from 'vitest';
import { createFakeExtension } from '$test-support/fake-extension';
import { stubFetch } from '$test-support/stub-fetch';
import { openLumiaClient } from './lumia-session';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('openLumiaClient', () => {
	it('gives no client until an instance address is stored', async () => {
		const { extension } = createFakeExtension();
		expect(await openLumiaClient(extension.storage.local)).toBeNull();
	});

	it('talks to the api of the stored instance with the stored token', async () => {
		const { extension } = createFakeExtension({
			stored: {
				'lumia.instance_url': 'https://lumia.example.com',
				'lumia.access_token': 'stored-access',
				'lumia.refresh_token': 'stored-refresh'
			}
		});
		const { requests } = stubFetch([{ status: 200, body: [] }]);
		const client = await openLumiaClient(extension.storage.local);
		await client?.article.listArticles();
		expect(requests[0].url).toBe('https://lumia.example.com/api/articles');
		expect(requests[0].authorization).toBe('Bearer stored-access');
	});
});
