import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createFakeExtension } from '$test-support/fake-extension';
import { articleSummary, feed, stubRoutes } from '$test-support/stub-fetch';
import { openLumiaClient } from '$technical/api/lumia-session';
import { en } from '$technical/i18n/messages/en';
import ArticleList from './article-list.svelte';

const SIGNED_IN = {
	'lumia.instance_url': 'https://lumia.test',
	'lumia.access_token': 'access',
	'lumia.refresh_token': 'refresh'
};

afterEach(() => {
	vi.unstubAllGlobals();
});

async function mountList(onsessionlost = vi.fn()) {
	const fake = createFakeExtension({ stored: SIGNED_IN });
	const client = (await openLumiaClient(fake.extension.storage.local))!;
	render(ArticleList, { client, onsessionlost });
	return { onsessionlost };
}

describe('ArticleList', () => {
	it('shows the newest articles as cards linking to the reading view', async () => {
		stubRoutes({
			'GET /feeds': { status: 200, body: [feed()] },
			'GET /articles?limit=20&offset=0': {
				status: 200,
				body: [
					articleSummary({ id: 'a1', title: 'First' }),
					articleSummary({ id: 'a2', title: 'Second' })
				]
			}
		});
		await mountList();

		const first = await screen.findByText('First');
		expect(first.closest('a')).toHaveAttribute('href', '#article/a1');
		expect(screen.getByText('Second').closest('a')).toHaveAttribute('href', '#article/a2');
	});

	it('labels reading time with the extension language', async () => {
		stubRoutes({
			'GET /feeds': { status: 200, body: [] },
			'GET /articles?limit=20&offset=0': {
				status: 200,
				body: [articleSummary({ reading_minutes: 7 })]
			}
		});
		await mountList();
		expect(await screen.findByText('7 min')).toBeInTheDocument();
	});

	it('shows placeholders while loading', async () => {
		stubRoutes({
			'GET /feeds': { status: 200, body: [] },
			'GET /articles?limit=20&offset=0': { status: 200, body: [] }
		});
		await mountList();
		expect(screen.getByRole('status', { name: en['reader.loading'] })).toBeInTheDocument();
		expect(await screen.findByText(en['reader.empty'])).toBeInTheDocument();
	});

	it('narrows to one feed', async () => {
		const { requests } = stubRoutes({
			'GET /feeds': { status: 200, body: [feed({ id: 'feed-9', title: 'Atelier' })] },
			'GET /articles?limit=20&offset=0': { status: 200, body: [] },
			'GET /articles?feed_id=feed-9&limit=20&offset=0': {
				status: 200,
				body: [articleSummary({ id: 'a9', title: 'From the atelier' })]
			}
		});
		await mountList();

		await within(await screen.findByLabelText(en['reader.feedFilter'])).findByText('Atelier');
		await userEvent.selectOptions(screen.getByLabelText(en['reader.feedFilter']), 'feed-9');

		expect(await screen.findByText('From the atelier')).toBeInTheDocument();
		expect(requests.at(-1)?.url).toContain('feed_id=feed-9');
	});

	it('narrows to the unread articles', async () => {
		stubRoutes({
			'GET /feeds': { status: 200, body: [] },
			'GET /articles?limit=20&offset=0': { status: 200, body: [] },
			'GET /articles?unread_only=true&limit=20&offset=0': {
				status: 200,
				body: [articleSummary({ title: 'Still unread' })]
			}
		});
		await mountList();

		await userEvent.click(await screen.findByLabelText(en['reader.unreadOnly']));

		expect(await screen.findByText('Still unread')).toBeInTheDocument();
	});

	it('loads the next page and stops offering it when the last one comes back short', async () => {
		const fullPage = Array.from({ length: 20 }, (_, index) =>
			articleSummary({ id: `a${index}`, title: `Article ${index}` })
		);
		stubRoutes({
			'GET /feeds': { status: 200, body: [] },
			'GET /articles?limit=20&offset=0': { status: 200, body: fullPage },
			'GET /articles?limit=20&offset=20': {
				status: 200,
				body: [articleSummary({ id: 'last', title: 'The last one' })]
			}
		});
		await mountList();

		await userEvent.click(await screen.findByRole('button', { name: en['reader.loadMore'] }));

		expect(await screen.findByText('The last one')).toBeInTheDocument();
		expect(screen.getByText('Article 0')).toBeInTheDocument();
		expect(screen.queryByRole('button', { name: en['reader.loadMore'] })).toBeNull();
	});

	it('offers a retry after a failure and recovers', async () => {
		stubRoutes({
			'GET /feeds': { status: 200, body: [] },
			'GET /articles?limit=20&offset=0': [
				{ status: 500 },
				{ status: 200, body: [articleSummary({ title: 'Back again' })] }
			]
		});
		await mountList();

		expect(await screen.findByRole('alert')).toHaveTextContent(en['reader.loadFailed']);
		await userEvent.click(screen.getByRole('button', { name: en['reader.retry'] }));

		expect(await screen.findByText('Back again')).toBeInTheDocument();
	});

	it('keeps the list when only the feed filter cannot load', async () => {
		stubRoutes({
			'GET /feeds': { status: 500 },
			'GET /articles?limit=20&offset=0': {
				status: 200,
				body: [articleSummary({ title: 'Still here' })]
			}
		});
		await mountList();
		expect(await screen.findByText('Still here')).toBeInTheDocument();
	});

	it('tells its parent when the session is gone', async () => {
		stubRoutes({
			'GET /feeds': { status: 401 },
			'GET /articles?limit=20&offset=0': { status: 401 },
			'POST /auth/refresh': { status: 401 }
		});
		const { onsessionlost } = await mountList();
		await screen.findByRole('alert');
		expect(onsessionlost).toHaveBeenCalled();
	});
});
