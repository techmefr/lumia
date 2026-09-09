import type { ArticleSummary } from '@lumia/core';
import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ArticleGrid from './article-grid.svelte';

type Props = Parameters<typeof ArticleGrid>[1];

function article(id: string, overrides: Partial<ArticleSummary> = {}): ArticleSummary {
	return {
		id,
		title: `Titre ${id}`,
		summary: null,
		url: `https://example.test/${id}`,
		image_url: null,
		source_label: 'Atelier Papier',
		feed_id: 'feed-1',
		published_at: '2026-08-09T08:30:00Z',
		reading_minutes: 4,
		read: false,
		scroll_progress: 0,
		relevance_score: null,
		...overrides
	} as ArticleSummary;
}

const THREE = [article('a'), article('b'), article('c')];

function grid(props: Partial<Props> = {}) {
	const { container } = render(ArticleGrid, {
		articles: THREE,
		loading: false,
		...props
	} as Props);

	return {
		container,
		root: () => container.querySelector('[data-test-article-grid]'),
		loader: () => container.querySelector('[data-test-grid-loading]'),
		emptyNotice: () => container.querySelector('[data-test-grid-empty]'),
		skeletons: () => [...container.querySelectorAll('[data-test-article-card-skeleton]')],
		cards: () => [...container.querySelectorAll('[data-test-article-card]')],
		cardIds: () =>
			[...container.querySelectorAll('[data-test-article-card]')].map((node) =>
				node.getAttribute('data-test-article-card')
			),
		hero: () => container.querySelector('[data-test-article-hero]'),
		ringed: () => [...container.querySelectorAll('.ring-2')]
	};
}

describe('while it is loading', () => {
	// Skeletons rather than a spinner, and shaped like the cards that are coming: the grid does not
	// reflow when the data lands, so what the reader was looking at stays where it was.
	it('shows placeholders instead of a spinner', () => {
		const view = grid({ articles: [], loading: true });
		expect(view.skeletons()).toHaveLength(6);
	});

	it('announces the wait to a screen reader', () => {
		const view = grid({ articles: [], loading: true });
		expect(view.loader()?.getAttribute('role')).toBe('status');
		expect(view.loader()?.getAttribute('aria-label')).toBeTruthy();
	});

	it('adds a lead placeholder in the kiosque layout', () => {
		const view = grid({ articles: [], loading: true, hero: true });
		expect(view.skeletons()).toHaveLength(7);
	});

	// Loading more at the bottom of a page that already has articles must not replace them with
	// placeholders: that is a full-page flash on every "load more".
	it('keeps showing the articles it already has', () => {
		const view = grid({ articles: THREE, loading: true });
		expect(view.loader()).toBeNull();
		expect(view.cards()).toHaveLength(3);
	});
});

describe('when there is nothing to show', () => {
	it('says so rather than showing an empty grid', () => {
		const view = grid({ articles: [], loading: false });
		expect(view.emptyNotice()).not.toBeNull();
		expect(view.root()).toBeNull();
	});

	it('shows no placeholders once the loading is over', () => {
		const view = grid({ articles: [], loading: false });
		expect(view.skeletons()).toHaveLength(0);
	});
});

describe('the articles', () => {
	it('renders one card per article, in order', () => {
		expect(grid().cardIds()).toEqual(['a', 'b', 'c']);
	});

	it('links each card to its article', () => {
		const href = grid().cards()[0].getAttribute('href');
		expect(href?.endsWith('/articles/a')).toBe(true);
	});

	it('passes the article through to the card', () => {
		const first = grid().cards()[0];
		expect(first.textContent).toContain('Titre a');
		expect(first.textContent).toContain('Atelier Papier');
	});

	it('marks a read article as read', () => {
		const view = grid({ articles: [article('a', { read: true })] });
		expect(view.cards()[0].getAttribute('data-test-read')).toBe('true');
	});
});

describe('the kiosque layout', () => {
	// The lead is the same article, rendered large: pulling it out of the grid rather than
	// duplicating it is what keeps the counts and the keyboard cursor honest.
	it('promotes the first article to a full-width lead', () => {
		const view = grid({ hero: true });
		expect(view.hero()?.getAttribute('data-test-article-hero')).toBe('a');
		expect(view.cardIds()).toEqual(['b', 'c']);
	});

	it('renders no lead without the kiosque layout', () => {
		expect(grid().hero()).toBeNull();
	});

	it('features the first card instead when there is no lead', () => {
		expect(grid().cards()[0].className).toContain('sm:col-span-2');
	});

	it('features no card in the grid when the lead already carries the emphasis', () => {
		const view = grid({ hero: true });
		expect(view.cards()[0].className).not.toContain('sm:col-span-2');
	});

	it('copes with a single article in the kiosque layout', () => {
		const view = grid({ articles: [article('a')], hero: true });
		expect(view.hero()).not.toBeNull();
		expect(view.cards()).toHaveLength(0);
	});
});

describe('the keyboard cursor', () => {
	it('rings nothing before the navigation has started', () => {
		expect(grid({ cursor: -1 }).ringed()).toHaveLength(0);
	});

	it('rings the card the cursor is on', () => {
		const view = grid({ cursor: 1 });
		expect(view.ringed()).toHaveLength(1);
		expect(view.ringed()[0].getAttribute('data-test-article-card')).toBe('b');
	});

	// The lead is index 0 of the articles but sits outside the grid, so every grid index shifts by
	// one. Getting this wrong rings the card next to the one j and k moved to.
	it('rings the lead when the cursor is on the first article', () => {
		const view = grid({ hero: true, cursor: 0 });
		expect(view.hero()?.className).toContain('ring-2');
		expect(view.cards().filter((card) => card.className.includes('ring-2'))).toHaveLength(0);
	});

	it('follows the shifted indices in the kiosque layout', () => {
		const view = grid({ hero: true, cursor: 2 });
		const ringed = view.cards().filter((card) => card.className.includes('ring-2'));
		expect(ringed).toHaveLength(1);
		expect(ringed[0].getAttribute('data-test-article-card')).toBe('c');
	});

	it('rings nothing for a cursor past the end', () => {
		expect(grid({ cursor: 99 }).ringed()).toHaveLength(0);
	});
});
