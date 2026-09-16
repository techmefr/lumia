import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import { articleSummary } from '../test-support/fixtures';
import ReadPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

let stubUrl = new URL('http://test/lire');
vi.mock('$app/state', () => ({
	page: {
		get url() {
			return stubUrl;
		}
	}
}));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		article: { listArticles: vi.fn() },
		recommendation: { sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

function readPage() {
	const { container } = render(ReadPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		heading: () => q('h1')!,
		loading: () => q('[role="status"]'),
		error: () => q('[role="alert"]'),
		topCard: () => q('[data-test-swipe-card="top"]'),
		like: () => q<HTMLButtonElement>('[data-test-swipe-like]')!,
		save: () => q<HTMLButtonElement>('[data-test-swipe-save]')!
	};
}

/** The parameters the list was asked for, which is how the page carries its url scope. */
function listRequest(): Record<string, unknown> {
	return api.article.listArticles.mock.calls[0][0] as Record<string, unknown>;
}

beforeEach(() => {
	stubUrl = new URL('http://test/lire');
	api.user.isAuthenticated.mockReturnValue(true);
	api.article.listArticles.mockResolvedValue([articleSummary('a'), articleSummary('b')]);
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('opening swipe mode', () => {
	it('scopes the pile to the feed named in the url', async () => {
		stubUrl = new URL('http://test/lire?feed_id=feed-3');
		readPage();

		await waitFor(() => expect(api.article.listArticles).toHaveBeenCalled());
		expect(listRequest()).toMatchObject({ feedId: 'feed-3' });
	});

	it('scopes the pile to the folder named in the url', async () => {
		stubUrl = new URL('http://test/lire?folder_id=folder-3');
		readPage();

		await waitFor(() => expect(api.article.listArticles).toHaveBeenCalled());
		expect(listRequest()).toMatchObject({ folderId: 'folder-3' });
	});

	// The label is what tells the reader which feed they are swiping through, since the pile itself
	// carries no source of its own.
	it('names the scope in the heading when the url carries a label', async () => {
		stubUrl = new URL('http://test/lire?feed_id=feed-3&label=Atelier%20Papier');
		const view = readPage();

		await waitFor(() => expect(view.heading().textContent).toContain('Atelier Papier'));
	});

	it('says the pile is empty when the scope holds nothing', async () => {
		api.article.listArticles.mockResolvedValue([]);
		const view = readPage();

		await waitFor(() => expect(view.loading()).toBeNull());
		expect(view.topCard()).toBeNull();
	});

	it('says so when the pile cannot be fetched', async () => {
		api.article.listArticles.mockRejectedValue(new Error('offline'));
		const view = readPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		readPage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(api.article.listArticles).not.toHaveBeenCalled();
	});
});

describe('working through the pile', () => {
	it('records a vote and drops the card', async () => {
		const view = readPage();
		await waitFor(() => expect(view.topCard()).not.toBeNull());

		await fireEvent.click(view.like());

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { sentiment: 'like' })
		);
	});

	it('empties the pile once every card has been voted on', async () => {
		api.article.listArticles.mockResolvedValue([articleSummary('a')]);
		const view = readPage();
		await waitFor(() => expect(view.topCard()).not.toBeNull());

		await fireEvent.click(view.like());

		await waitFor(() => expect(view.topCard()).toBeNull());
	});

	it('keeps a saved card on the pile', async () => {
		const view = readPage();
		await waitFor(() => expect(view.topCard()).not.toBeNull());

		await fireEvent.click(view.save());

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { saved: true })
		);
		expect(view.topCard()).not.toBeNull();
	});
});
