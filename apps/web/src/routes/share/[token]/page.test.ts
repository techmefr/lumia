import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { PublicArticle } from '@lumia/core';
import { lumia } from '$technical/api/client';
import { setLocale } from '$technical/i18n/i18n.svelte';
import SharePage from './+page.svelte';

let params: Record<string, string> = { token: 'a-public-token' };
vi.mock('$app/state', () => ({
	page: {
		get params() {
			return params;
		}
	}
}));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { article: { getPublicArticle: vi.fn() } }
}));

const api = vi.mocked(lumia.article);

function shared(overrides: Partial<PublicArticle> = {}): PublicArticle {
	return {
		title: 'Le papier et l encre',
		content: '<p>Un corps.</p>',
		url: 'https://example.test/papier',
		published_at: '2026-08-09T08:30:00Z',
		author_name: 'Ada Lovelace',
		image_url: null,
		language: 'fr',
		...overrides
	};
}

function sharePage() {
	const { container } = render(SharePage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loading: () => q('[role="status"]'),
		missing: () => q('[data-test-public-missing]'),
		title: () => q('[data-test-public-title]'),
		content: () => q('[data-test-public-content]'),
		source: () => q<HTMLAnchorElement>('[data-test-public-source]'),
		print: () => q<HTMLButtonElement>('[data-test-print-button]')!,
		article: () => q('[data-test-public-article]')
	};
}

async function loaded() {
	const view = sharePage();
	await waitFor(() => expect(view.title()).not.toBeNull());
	return view;
}

beforeEach(() => {
	setLocale('fr');
	params = { token: 'a-public-token' };
	api.getPublicArticle.mockResolvedValue(shared());
});

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
	document.head.querySelectorAll('meta[name="robots"], meta[name="referrer"]').forEach((m) => m.remove());
});

describe('opening a shared article', () => {
	it('asks for the article behind the token in the address', async () => {
		await loaded();

		expect(api.getPublicArticle).toHaveBeenCalledWith('a-public-token');
	});

	it('shows a placeholder while the article is on its way', async () => {
		let release: (value: PublicArticle) => void = () => {};
		api.getPublicArticle.mockReturnValue(new Promise((resolve) => (release = resolve)));

		const view = sharePage();

		expect(view.loading()).not.toBeNull();
		release(shared());
		await waitFor(() => expect(view.loading()).toBeNull());
	});

	it('renders the title, the author and the body, and the language of the article', async () => {
		const view = await loaded();

		expect(view.title()?.textContent).toContain('Le papier et l encre');
		expect(view.content()?.textContent).toContain('Un corps.');
		expect(view.article()?.textContent).toContain('Ada Lovelace');
		expect(view.article()?.getAttribute('lang')).toBe('fr');
	});

	it('sanitizes the body again in the browser, whatever the server sent', async () => {
		api.getPublicArticle.mockResolvedValue(
			shared({ content: '<p>Texte</p><img src="x" onerror="alert(1)"><script>alert(2)</script>' })
		);

		const view = await loaded();

		expect(view.content()?.innerHTML).not.toContain('onerror');
		expect(view.content()?.innerHTML).not.toContain('<script');
	});

	it('links to the original without leaking where it was read from', async () => {
		const view = await loaded();

		expect(view.source()?.getAttribute('href')).toBe('https://example.test/papier');
		expect(view.source()?.getAttribute('rel')).toContain('noopener');
		expect(view.source()?.getAttribute('rel')).toContain('nofollow');
	});

	it('is not indexable and does not send a referrer', async () => {
		await loaded();

		expect(document.head.querySelector('meta[name="robots"]')?.getAttribute('content')).toContain(
			'noindex'
		);
		expect(document.head.querySelector('meta[name="referrer"]')?.getAttribute('content')).toBe(
			'no-referrer'
		);
	});

	it('can be printed', async () => {
		const print = vi.fn();
		vi.stubGlobal('print', print);
		const view = await loaded();

		await fireEvent.click(view.print());

		expect(print).toHaveBeenCalledOnce();
	});

	it('shows the cover when there is one', async () => {
		api.getPublicArticle.mockResolvedValue(shared({ image_url: 'https://example.test/c.png' }));

		const view = await loaded();

		expect(view.container.querySelector('img')?.getAttribute('referrerpolicy')).toBe('no-referrer');
	});

	it('says the link is unknown when the instance refuses it, without saying why', async () => {
		api.getPublicArticle.mockRejectedValue(new Error('404'));

		const view = sharePage();

		await waitFor(() => expect(view.missing()).not.toBeNull());
		expect(view.title()).toBeNull();
	});

	it('asks for nothing when the address carries no token', async () => {
		params = {};

		const view = sharePage();

		await waitFor(() => expect(view.missing()).not.toBeNull());
		expect(api.getPublicArticle).not.toHaveBeenCalled();
	});
});
