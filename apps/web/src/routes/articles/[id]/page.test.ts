import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import type { ArticleDetail } from '@lumia/core';
import { articleDetail } from '../../test-support/fixtures';
import ArticlePage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

let params: Record<string, string> = { id: 'article-1' };
vi.mock('$app/state', () => ({
	page: {
		get params() {
			return params;
		}
	}
}));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		article: { getArticle: vi.fn(), translateArticle: vi.fn() },
		playlist: { listPlaylists: vi.fn(), addArticle: vi.fn(), createPlaylist: vi.fn() },
		recommendation: { sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

function articlePage() {
	const { container } = render(ArticlePage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loading: () => q('[role="status"]'),
		error: () => q('[role="alert"]'),
		heading: () => q('[data-test-article-heading]'),
		content: () => q('[data-test-article-content]'),
		like: () => q<HTMLButtonElement>('[data-test-like]')!,
		dislike: () => q<HTMLButtonElement>('[data-test-dislike]')!,
		save: () => q<HTMLButtonElement>('[data-test-save]')!,
		favorite: () => q<HTMLButtonElement>('[data-test-favorite]')!,
		share: () => q<HTMLButtonElement>('[data-test-share]')!,
		filterLinks: () => [...container.querySelectorAll<HTMLAnchorElement>('a[href*="/articles?"]')]
	};
}

/** The payload of the nth feedback call, which is what the page's actions turn a click into. */
function feedbackPayload(index: number): Record<string, unknown> {
	return api.recommendation.sendFeedback.mock.calls[index][1] as Record<string, unknown>;
}

async function loaded() {
	const view = articlePage();
	await waitFor(() => expect(view.heading()).not.toBeNull());
	return view;
}

beforeEach(() => {
	params = { id: 'article-1' };
	api.user.isAuthenticated.mockReturnValue(true);
	api.article.getArticle.mockResolvedValue(articleDetail('article-1'));
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
	api.playlist.listPlaylists.mockResolvedValue([]);
});

afterEach(() => {
	// `globals` is off in this project, so testing-library never registers its own cleanup and a
	// page from a previous test would keep its document and window listeners bound.
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('opening an article', () => {
	it('shows a placeholder while the body is on its way', async () => {
		let release: (value: ArticleDetail) => void = () => {};
		api.article.getArticle.mockReturnValue(new Promise((resolve) => (release = resolve)));

		const view = articlePage();

		expect(view.loading()).not.toBeNull();
		release(articleDetail('article-1'));
		await waitFor(() => expect(view.loading()).toBeNull());
	});

	it('renders the title and the body once loaded', async () => {
		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', { title: 'Le papier et l encre', content: '<p>Un corps.</p>' })
		);

		const view = await loaded();

		expect(view.heading()?.textContent).toContain('Le papier et l encre');
		expect(view.content()?.textContent).toContain('Un corps.');
	});

	it('says the article cannot be found when the request fails', async () => {
		api.article.getArticle.mockRejectedValue(new Error('gone'));

		const view = articlePage();

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.heading()).toBeNull();
	});

	it('asks for nothing and reports a missing article when the route carries no id', async () => {
		params = {};

		const view = articlePage();

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(api.article.getArticle).not.toHaveBeenCalled();
	});

	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		articlePage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/login');
		expect(api.article.getArticle).not.toHaveBeenCalled();
	});
});

describe('reacting to an article', () => {
	it('records a like, then withdraws it when the same button is pressed again', async () => {
		const view = await loaded();

		await fireEvent.click(view.like());
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(1));
		expect(feedbackPayload(0)).toEqual({ sentiment: 'like' });

		await fireEvent.click(view.like());
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(2));
		expect(feedbackPayload(1)).toEqual({ sentiment: null });
	});

	it('replaces a like by a dislike rather than stacking the two', async () => {
		const view = await loaded();

		await fireEvent.click(view.like());
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(1));
		await fireEvent.click(view.dislike());

		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(2));
		expect(feedbackPayload(1)).toEqual({ sentiment: 'dislike' });
	});

	it('saves the article for later and unsaves it on a second press', async () => {
		const view = await loaded();

		await fireEvent.click(view.save());
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(1));
		expect(feedbackPayload(0)).toEqual({ saved: true });

		await fireEvent.click(view.save());
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(2));
		expect(feedbackPayload(1)).toEqual({ saved: false });
	});

	it('marks the article as a favourite', async () => {
		const view = await loaded();

		await fireEvent.click(view.favorite());

		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(1));
		expect(feedbackPayload(0)).toEqual({ favorite: true });
	});
});

describe('sharing an article', () => {
	it('hands the title and the url to the system share sheet when there is one', async () => {
		const share = vi.fn().mockResolvedValue(undefined);
		vi.stubGlobal('navigator', { ...navigator, share });
		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', { url: 'https://example.test/papier' })
		);
		const view = await loaded();

		await fireEvent.click(view.share());

		await waitFor(() => expect(share).toHaveBeenCalled());
		expect(share.mock.calls[0][0]).toMatchObject({ url: 'https://example.test/papier' });
	});

	// Desktop browsers have no share sheet, so the link goes to the clipboard and the button has to
	// say so — otherwise the press looks like it did nothing at all.
	it('copies the link and confirms it when no share sheet exists', async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		vi.stubGlobal('navigator', { ...navigator, share: undefined, clipboard: { writeText } });
		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', { url: 'https://example.test/papier' })
		);
		const view = await loaded();

		await fireEvent.click(view.share());

		await waitFor(() => expect(writeText).toHaveBeenCalledWith('https://example.test/papier'));
		await waitFor(() => expect(view.share().textContent?.trim()).not.toBe(''));
	});
});

describe('the article metadata', () => {
	it('links the author, the category and every keyword back to a filtered list', async () => {
		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', {
				author_id: 'author-7',
				author_name: 'Camille',
				category_id: 'cat-3',
				category_name: 'Design',
				keywords: [{ id: 'kw-1', term: 'typographie' }]
			})
		);

		const view = await loaded();

		const hrefs = view.filterLinks().map((link) => link.getAttribute('href') ?? '');
		expect(hrefs.some((href) => href.includes('author_id=author-7'))).toBe(true);
		expect(hrefs.some((href) => href.includes('category_id=cat-3'))).toBe(true);
		expect(hrefs.some((href) => href.includes('keyword_id=kw-1'))).toBe(true);
	});

	it('leaves out the author and category chips when the article carries neither', async () => {
		const view = await loaded();

		const hrefs = view.filterLinks().map((link) => link.getAttribute('href') ?? '');
		expect(hrefs.some((href) => href.includes('author_id='))).toBe(false);
		expect(hrefs.some((href) => href.includes('category_id='))).toBe(false);
	});
});

describe('following the reader down the page', () => {
	function stubScroll(scrollY: number, scrollHeight = 2000, innerHeight = 1000) {
		vi.spyOn(document.documentElement, 'scrollHeight', 'get').mockReturnValue(scrollHeight);
		vi.stubGlobal('innerHeight', innerHeight);
		vi.stubGlobal('scrollY', scrollY);
	}

	it('records how far reading got', async () => {
		await loaded();
		stubScroll(500);

		await fireEvent.scroll(window);

		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalled());
		expect(feedbackPayload(0)).toEqual({ scroll_progress: 0.5 });
	});

	// Landing on the page and not moving is not reading, and writing it would overwrite a real
	// position recorded on an earlier visit.
	it('records nothing while the reader has barely moved', async () => {
		await loaded();
		stubScroll(5);

		await fireEvent.scroll(window);

		expect(api.recommendation.sendFeedback).not.toHaveBeenCalled();
	});

	it('marks the article read once the reader reaches the end', async () => {
		await loaded();
		stubScroll(950);

		await fireEvent.scroll(window);

		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalled());
		const payloads = api.recommendation.sendFeedback.mock.calls.map((call) => call[1]);
		expect(payloads).toContainEqual({ read: true });
	});

	it('does not mark an already-read article read a second time', async () => {
		api.article.getArticle.mockResolvedValue(articleDetail('article-1', { read: true }));
		await loaded();
		stubScroll(950);

		await fireEvent.scroll(window);

		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalled());
		const payloads = api.recommendation.sendFeedback.mock.calls.map((call) => call[1]);
		expect(payloads).not.toContainEqual({ read: true });
	});
});
