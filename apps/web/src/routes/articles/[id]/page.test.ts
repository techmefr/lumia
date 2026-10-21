import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import { setLocale } from '$technical/i18n/i18n.svelte';
import type { ArticleDetail } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { articleDetail, highlight, me } from '../../test-support/fixtures';
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
		user: { isAuthenticated: vi.fn(() => true), getMe: vi.fn() },
		article: { getArticle: vi.fn(), translateArticle: vi.fn(), getRelatedArticles: vi.fn() },
		playlist: { listPlaylists: vi.fn(), addArticle: vi.fn(), createPlaylist: vi.fn() },
		recommendation: { sendFeedback: vi.fn() },
		highlight: {
			listArticleHighlights: vi.fn(),
			createHighlight: vi.fn(),
			updateHighlightNote: vi.fn(),
			deleteHighlight: vi.fn()
		}
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
		video: () => q<HTMLIFrameElement>('[data-test-video-player]'),
		like: () => q<HTMLButtonElement>('[data-test-like]')!,
		dislike: () => q<HTMLButtonElement>('[data-test-dislike]')!,
		orbitToggle: () => q<HTMLButtonElement>('[data-test-orbit-toggle]')!,
		orbitAction: (id: string) => q<HTMLButtonElement>(`[data-test-orbit-action="${id}"]`),
		// Save, favourite and share live in the orbit menu, which is a menu button: its items are
		// only in the dom once the trigger has been opened.
		orbit: async (id: string) => {
			await fireEvent.click(q<HTMLButtonElement>('[data-test-orbit-toggle]')!);
			await waitFor(() => expect(q(`[data-test-orbit-action="${id}"]`)).not.toBeNull());
			await fireEvent.click(q<HTMLButtonElement>(`[data-test-orbit-action="${id}"]`)!);
		},
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
	api.user.getMe.mockResolvedValue(me());
	api.article.getArticle.mockResolvedValue(articleDetail('article-1'));
	api.article.getRelatedArticles.mockResolvedValue([]);
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
	api.playlist.listPlaylists.mockResolvedValue([]);
	api.highlight.listArticleHighlights.mockResolvedValue([]);
});

afterEach(() => {
	// `globals` is off in this project, so testing-library never registers its own cleanup and a
	// page from a previous test would keep its document and window listeners bound.
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('opening an article', () => {
	it('embeds a youtube video through the cookie-free player', async () => {
		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', { url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' })
		);

		const view = await loaded();

		expect(view.video()?.getAttribute('src')).toBe(
			'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ'
		);
		expect(view.video()?.getAttribute('title')).toBeTruthy();
	});

	it('shows no player for an ordinary article', async () => {
		const view = await loaded();

		expect(view.video()).toBeNull();
	});

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

	it('links to the source page of a web article but not of a mailed newsletter', async () => {
		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', { url: 'https://example.com/a' })
		);
		await loaded();
		expect(document.querySelector('[data-test-read-source]')).not.toBeNull();
		cleanup();

		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', { url: 'urn:lumia:newsletter:abc' })
		);
		await loaded();
		expect(document.querySelector('[data-test-read-source]')).toBeNull();
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

		await view.orbit('save');
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(1));
		expect(feedbackPayload(0)).toEqual({ saved: true });

		await view.orbit('save');
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(2));
		expect(feedbackPayload(1)).toEqual({ saved: false });
	});

	it('marks the article as a favourite', async () => {
		const view = await loaded();

		await view.orbit('favorite');

		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalledTimes(1));
		expect(feedbackPayload(0)).toEqual({ favorite: true });
	});

	// The menu items that toggle are checkboxes, so the state they carry is what tells the reader
	// the article is already saved when they come back to it.
	it('shows the article as saved once it has been put aside', async () => {
		const view = await loaded();

		await view.orbit('save');
		await waitFor(() => expect(api.recommendation.sendFeedback).toHaveBeenCalled());
		await fireEvent.click(view.orbitToggle());

		await waitFor(() =>
			expect(view.orbitAction('save')?.getAttribute('aria-checked')).toBe('true')
		);
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

		await view.orbit('share');

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

		await view.orbit('share');

		await waitFor(() => expect(writeText).toHaveBeenCalledWith('https://example.test/papier'));
		// Running an action closes the menu, so the confirmation is read where it is written: on the
		// share item itself, the next time the menu is opened.
		await fireEvent.click(view.orbitToggle());
		await waitFor(() =>
			expect(view.orbitAction('share')?.textContent).toContain('Link copied')
		);
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

describe('printing', () => {
	it('hands the page to the browser print dialog', async () => {
		const print = vi.fn();
		vi.stubGlobal('print', print);
		const view = await loaded();

		await fireEvent.click(view.container.querySelector<HTMLButtonElement>('[data-test-print-button]')!);

		expect(print).toHaveBeenCalledOnce();
	});

	it('carries the source address and the date for the paper copy', async () => {
		api.article.getArticle.mockResolvedValue(
			articleDetail('article-1', { url: 'https://example.test/papier', published_at: '2026-08-09T08:30:00Z' })
		);
		const view = await loaded();

		const source = view.container.querySelector('[data-test-print-source]')?.textContent ?? '';

		expect(source).toContain('https://example.test/papier');
		expect(source).toMatch(/2026/);
	});
});

describe('highlights in the article', () => {
	const BODY = '<p>Sur le papier et l encre.</p>';

	/** What a reader does: drag across words, which the browser reports as a selection change. */
	async function select(from: number, to: number) {
		const text = document.querySelector('[data-test-article-content] p')!.firstChild!;
		const range = document.createRange();
		range.setStart(text, from);
		range.setEnd(text, to);
		const selection = document.getSelection()!;
		selection.removeAllRanges();
		selection.addRange(range);
		document.dispatchEvent(new Event('selectionchange'));
	}

	const addButton = () => document.querySelector<HTMLButtonElement>('[data-test-highlight-add]');
	const cards = () => [...document.querySelectorAll('[data-test-highlight]')];

	beforeEach(() => {
		setLocale('en');
		api.article.getArticle.mockResolvedValue(articleDetail('article-1', { content: BODY }));
		for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	});

	it('lists the highlights stored for the article', async () => {
		api.highlight.listArticleHighlights.mockResolvedValue([
			highlight('h1', { quote: 'papier', start_offset: 7, end_offset: 13 })
		]);

		await loaded();

		await waitFor(() => expect(cards()).toHaveLength(1));
		expect(api.highlight.listArticleHighlights).toHaveBeenCalledWith('article-1');
	});

	it('shows no highlights section for an article without any', async () => {
		await loaded();

		expect(document.querySelector('[data-test-highlights]')).toBeNull();
	});

	it('offers to highlight a selection, and nothing when the selection goes away', async () => {
		await loaded();
		expect(addButton()).toBeNull();

		await select(7, 13);
		await waitFor(() => expect(addButton()).not.toBeNull());

		document.getSelection()!.removeAllRanges();
		document.dispatchEvent(new Event('selectionchange'));
		await waitFor(() => expect(addButton()).toBeNull());
	});

	it('saves the selected passage and lists it', async () => {
		api.highlight.createHighlight.mockImplementation(async (_id, draft) =>
			highlight('new', { ...draft, note: null })
		);
		await loaded();
		await select(7, 13);
		await waitFor(() => expect(addButton()).not.toBeNull());

		await fireEvent.click(addButton()!);

		await waitFor(() => expect(cards()).toHaveLength(1));
		expect(api.highlight.createHighlight).toHaveBeenCalledWith(
			'article-1',
			expect.objectContaining({ quote: 'papier', start_offset: 7, end_offset: 13 })
		);
		expect(addButton()).toBeNull();
	});

	it('says so when the highlight cannot be saved, and keeps the selection', async () => {
		api.highlight.createHighlight.mockRejectedValue(new Error('offline'));
		await loaded();
		await select(7, 13);
		await waitFor(() => expect(addButton()).not.toBeNull());

		await fireEvent.click(addButton()!);

		await waitFor(() => expect(toasts.toasts.some((item) => item.message.includes('highlight'))).toBe(true));
		expect(cards()).toHaveLength(0);
	});

	it('deletes a highlight from the list', async () => {
		api.highlight.listArticleHighlights.mockResolvedValue([
			highlight('h1', { quote: 'papier', start_offset: 7, end_offset: 13 })
		]);
		api.highlight.deleteHighlight.mockResolvedValue(undefined);
		await loaded();
		await waitFor(() => expect(cards()).toHaveLength(1));

		await fireEvent.click(document.querySelector<HTMLButtonElement>('[data-test-highlight-delete]')!);

		await waitFor(() => expect(cards()).toHaveLength(0));
		expect(api.highlight.deleteHighlight).toHaveBeenCalledWith('h1');
	});

	it('says so when a highlight cannot be deleted, and keeps it', async () => {
		api.highlight.listArticleHighlights.mockResolvedValue([highlight('h1')]);
		api.highlight.deleteHighlight.mockRejectedValue(new Error('offline'));
		await loaded();
		await waitFor(() => expect(cards()).toHaveLength(1));

		await fireEvent.click(document.querySelector<HTMLButtonElement>('[data-test-highlight-delete]')!);

		await waitFor(() => expect(api.highlight.deleteHighlight).toHaveBeenCalled());
		expect(cards()).toHaveLength(1);
	});

	it('saves a note on a highlight', async () => {
		api.highlight.listArticleHighlights.mockResolvedValue([highlight('h1')]);
		api.highlight.updateHighlightNote.mockImplementation(async (id, note) => highlight(id, { note }));
		await loaded();
		await waitFor(() => expect(cards()).toHaveLength(1));
		await fireEvent.click(document.querySelector<HTMLButtonElement>('[data-test-highlight-edit]')!);
		await fireEvent.input(document.querySelector<HTMLTextAreaElement>('[data-test-highlight-note-field]')!, {
			target: { value: 'A thought' }
		});

		await fireEvent.click(document.querySelector<HTMLButtonElement>('[data-test-highlight-note-save]')!);

		await waitFor(() =>
			expect(document.querySelector('[data-test-highlight-note]')?.textContent).toContain('A thought')
		);
		expect(api.highlight.updateHighlightNote).toHaveBeenCalledWith('h1', 'A thought');
	});

	it('says so when a note cannot be saved', async () => {
		api.highlight.listArticleHighlights.mockResolvedValue([highlight('h1')]);
		api.highlight.updateHighlightNote.mockRejectedValue(new Error('offline'));
		await loaded();
		await waitFor(() => expect(cards()).toHaveLength(1));
		await fireEvent.click(document.querySelector<HTMLButtonElement>('[data-test-highlight-edit]')!);

		await fireEvent.click(document.querySelector<HTMLButtonElement>('[data-test-highlight-note-save]')!);

		await waitFor(() => expect(toasts.toasts.some((item) => item.message.includes('note'))).toBe(true));
	});

	it('still shows the article when the highlights cannot be fetched', async () => {
		api.highlight.listArticleHighlights.mockRejectedValue(new Error('offline'));

		const view = await loaded();

		expect(view.content()?.textContent).toContain('Sur le papier');
		expect(view.error()).toBeNull();
	});
});
