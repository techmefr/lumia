import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createFakeExtension } from '$test-support/fake-extension';
import { articleSummary, stubRoutes } from '$test-support/stub-fetch';
import { openLumiaClient } from '$technical/api/lumia-session';
import { en } from '$technical/i18n/messages/en';
import ArticleReader from './article-reader.svelte';

const SIGNED_IN = {
	'lumia.instance_url': 'https://lumia.test',
	'lumia.access_token': 'access',
	'lumia.refresh_token': 'refresh'
};

const MARK_READ = 'POST /articles/mark-read';

afterEach(() => {
	vi.unstubAllGlobals();
});

async function mountReader(onsessionlost = vi.fn()) {
	const fake = createFakeExtension({ stored: SIGNED_IN });
	const client = (await openLumiaClient(fake.extension.storage.local))!;
	render(ArticleReader, { client, articleId: 'a1', onsessionlost });
	return { onsessionlost };
}

describe('ArticleReader', () => {
	it('shows the article and marks it as read', async () => {
		const { requests } = stubRoutes({
			'GET /articles/a1': {
				status: 200,
				body: {
					...articleSummary({ title: 'A long read', url: 'https://blog.test/long' }),
					content: '<p>The body.</p>',
					keywords: []
				}
			},
			[MARK_READ]: { status: 200, body: { updated: 1 } }
		});
		await mountReader();

		expect(await screen.findByRole('heading', { name: 'A long read' })).toBeInTheDocument();
		expect(screen.getByText('The body.')).toBeInTheDocument();
		await waitFor(() => expect(requests.map((request) => request.method + request.url)).toContain(
			'POSThttps://lumia.test/api/articles/mark-read'
		));
		expect(requests.find((request) => request.url.endsWith('/mark-read'))?.body).toEqual({
			article_ids: ['a1'],
			read: true
		});
	});

	it('strips scripts and forms from the third-party content', async () => {
		stubRoutes({
			'GET /articles/a1': {
				status: 200,
				body: {
					...articleSummary(),
					content:
						'<p>Safe</p><script>window.hacked = true</script><form><input name="password"></form><img src="x" onerror="window.hacked = true">',
					keywords: []
				}
			},
			[MARK_READ]: { status: 200, body: { updated: 1 } }
		});
		await mountReader();

		await screen.findByText('Safe');
		const content = document.querySelector('[data-test-article-content]')!;
		expect(content.querySelector('script, form, input')).toBeNull();
		expect(content.querySelector('img')?.hasAttribute('onerror')).toBe(false);
	});

	it('links back to the list and out to the original page, safely', async () => {
		stubRoutes({
			'GET /articles/a1': {
				status: 200,
				body: { ...articleSummary({ url: 'https://blog.test/long' }), content: '<p>x</p>', keywords: [] }
			},
			[MARK_READ]: { status: 200, body: { updated: 1 } }
		});
		await mountReader();

		const original = await screen.findByRole('link', { name: en['reader.openOriginal'] });
		expect(original).toHaveAttribute('href', 'https://blog.test/long');
		expect(original).toHaveAttribute('target', '_blank');
		expect(original).toHaveAttribute('rel', 'noopener noreferrer');
		expect(screen.getByRole('link', { name: en['reader.back'] })).toHaveAttribute('href', '#');
	});

	it('still shows the article when marking it read fails', async () => {
		stubRoutes({
			'GET /articles/a1': {
				status: 200,
				body: { ...articleSummary({ title: 'Readable' }), content: '<p>x</p>', keywords: [] }
			},
			[MARK_READ]: { status: 500 }
		});
		await mountReader();
		expect(await screen.findByRole('heading', { name: 'Readable' })).toBeInTheDocument();
	});

	it('offers a retry when the article cannot be loaded', async () => {
		stubRoutes({
			'GET /articles/a1': [
				{ status: 500 },
				{
					status: 200,
					body: { ...articleSummary({ title: 'Second try' }), content: '<p>x</p>', keywords: [] }
				}
			],
			[MARK_READ]: { status: 200, body: { updated: 1 } }
		});
		await mountReader();

		expect(await screen.findByRole('alert')).toHaveTextContent(en['reader.articleFailed']);
		await userEvent.click(screen.getByRole('button', { name: en['reader.retry'] }));

		expect(await screen.findByRole('heading', { name: 'Second try' })).toBeInTheDocument();
	});

	it('tells its parent when the session is gone', async () => {
		stubRoutes({
			'GET /articles/a1': { status: 401 },
			'POST /auth/refresh': { status: 401 }
		});
		const { onsessionlost } = await mountReader();
		await screen.findByRole('alert');
		expect(onsessionlost).toHaveBeenCalled();
	});
});

describe('ArticleReader original link', () => {
	it('is not offered when the article address is not http or https', async () => {
		stubRoutes({
			'GET /articles/a1': {
				status: 200,
				body: { ...articleSummary({ url: 'javascript:alert(1)' }), content: '<p>x</p>', keywords: [] }
			},
			[MARK_READ]: { status: 200, body: { updated: 1 } }
		});
		await mountReader();

		await screen.findByText('x');
		expect(screen.queryByRole('link', { name: en['reader.openOriginal'] })).toBeNull();
	});
});
