import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ArticleCard from './article-card.svelte';

type Props = Parameters<typeof ArticleCard>[1];

const BASE = {
	id: 'article-1',
	href: '/articles/article-1',
	title: 'Les kiosques numériques réinventent la une',
	sourceLabel: 'Atelier Papier',
	publishedAt: '2026-08-09T08:30:00Z',
	accentHue: 220
} satisfies Partial<Props>;

// Selectors are data-test-* rather than classes: the classes here exist for visual reasons and
// change on a design pass, which must not be able to take the suite down with it.
function card(overrides: Partial<Props> = {}) {
	const { container } = render(ArticleCard, { ...BASE, ...overrides } as Props);
	const root = container.querySelector('[data-test-article-card]')!;
	return {
		root,
		title: () => root.querySelector('[data-test-article-title]'),
		summary: () => root.querySelector('[data-test-article-summary]'),
		source: () => root.querySelector('[data-test-source-label]'),
		avatar: () => root.querySelector('[data-test-source-avatar]'),
		score: () => root.querySelector('[data-test-relevance-score]'),
		minutes: () => root.querySelector('[data-test-reading-minutes]'),
		date: () => root.querySelector('[data-test-published-date]'),
		progress: () => root.querySelector('[data-test-reading-progress]')
	};
}

describe('what the card always shows', () => {
	it('carries the article id, so a list can be addressed by article', () => {
		expect(card().root.getAttribute('data-test-article-card')).toBe('article-1');
	});

	it('shows the title', () => {
		expect(card().title()?.textContent?.trim()).toBe(BASE.title);
	});

	it('links to the article', () => {
		expect(card().root.getAttribute('href')).toBe('/articles/article-1');
	});

	it('names the source', () => {
		expect(card().source()?.textContent).toContain('Atelier Papier');
	});
});

describe('the source avatar', () => {
	it('falls back to the initial of the source when there is no icon', () => {
		expect(card().avatar()?.textContent?.trim()).toBe('A');
	});

	it('uppercases that initial even from a lowercase source name', () => {
		expect(card({ sourceLabel: 'atelier papier' }).avatar()?.textContent?.trim()).toBe('A');
	});

	it('shows the feed icon when one is given', () => {
		const image = card({ iconUrl: 'https://lumia.test/icon.png' })
			.avatar()
			?.querySelector('img');
		expect(image?.getAttribute('src')).toBe('https://lumia.test/icon.png');
	});

	it('leaves the icon out of the accessibility tree, the source being named next to it', () => {
		const image = card({ iconUrl: 'https://lumia.test/icon.png' })
			.avatar()
			?.querySelector('img');
		expect(image?.getAttribute('alt')).toBe('');
	});
});

describe('the relevance score', () => {
	it('is hidden at the neutral 50, where the number would say nothing', () => {
		expect(card({ relevanceScore: 50 }).score()).toBeNull();
	});

	it('is hidden when the backend sent none', () => {
		expect(card({ relevanceScore: null }).score()).toBeNull();
	});

	it('shows a score above the neutral point', () => {
		expect(card({ relevanceScore: 88 }).score()?.textContent).toContain('88');
	});

	it('shows a score below it too', () => {
		expect(card({ relevanceScore: 12 }).score()?.textContent).toContain('12');
	});

	// The bare number means nothing read aloud, so the scale is spelled out for a screen reader.
	it('spells the scale out for assistive technology', () => {
		const score = card({ relevanceScore: 88, scoreSuffix: 'sur 100 de pertinence' }).score();
		expect(score?.textContent).toContain('sur 100 de pertinence');
	});
});

describe('the reading time', () => {
	it('is left out when the backend has no word count', () => {
		expect(card({ readingMinutes: null }).minutes()).toBeNull();
	});

	it('uses the label the app hands over, so it is never in english by accident', () => {
		const rendered = card({
			readingMinutes: 4,
			minutesLabel: (minutes) => `${minutes} minutes de lecture`
		});
		expect(rendered.minutes()?.textContent?.trim()).toBe('4 minutes de lecture');
	});

	it('falls back to a neutral label when the app passes none', () => {
		expect(card({ readingMinutes: 4 }).minutes()?.textContent?.trim()).toBe('4 min');
	});
});

describe('a read article', () => {
	it('is flagged as read', () => {
		expect(card({ read: true }).root.getAttribute('data-test-read')).toBe('true');
	});

	it('is flagged unread by default', () => {
		expect(card().root.getAttribute('data-test-read')).toBe('false');
	});

	it('says so in words next to the source, not by colour alone', () => {
		expect(card({ read: true, readLabel: 'lu' }).source()?.textContent).toContain('lu');
	});

	it('says nothing of the sort when unread', () => {
		expect(card({ readLabel: 'lu' }).source()?.textContent).not.toContain('lu');
	});
});

describe('the reading progress bar', () => {
	it('is absent before the reader has started', () => {
		expect(card({ scrollProgress: 0 }).progress()).toBeNull();
	});

	it('is absent once finished, the card being marked read instead', () => {
		expect(card({ scrollProgress: 1 }).progress()).toBeNull();
	});

	it('shows the percentage reached part-way through', () => {
		expect(card({ scrollProgress: 0.42 }).progress()?.getAttribute('data-test-reading-progress')).toBe(
			'42'
		);
	});

	it('clamps a value the backend should never have sent', () => {
		expect(card({ scrollProgress: 4 }).progress()).toBeNull();
	});
});

describe('the summary', () => {
	it('is shown only on the featured card, where there is room for it', () => {
		expect(card({ summary: 'Un mouvement de fond.', featured: true }).summary()).not.toBeNull();
	});

	it('is left out of an ordinary card', () => {
		expect(card({ summary: 'Un mouvement de fond.' }).summary()).toBeNull();
	});
});

describe('the date', () => {
	it('is formatted in the locale the app hands over, not a hardcoded one', () => {
		const french = card({ locale: 'fr-FR' }).date()?.textContent?.trim();
		const english = card({ locale: 'en-US' }).date()?.textContent?.trim();
		expect(french).not.toBe(english);
	});

	it('reads as a day and a month in french', () => {
		expect(card({ locale: 'fr-FR' }).date()?.textContent?.trim()).toMatch(/^\d+ \p{L}+\.?$/u);
	});
});

describe('the cover image', () => {
	it('shows the article image when there is one', () => {
		const { root } = card({ imageUrl: 'https://lumia.test/cover.jpg' });
		expect(root.querySelector('img[src="https://lumia.test/cover.jpg"]')).not.toBeNull();
	});

	it('is decorative, the title carrying the meaning', () => {
		const { root } = card({ imageUrl: 'https://lumia.test/cover.jpg' });
		expect(root.querySelector('img[src="https://lumia.test/cover.jpg"]')?.getAttribute('alt')).toBe(
			''
		);
	});

	it('loads lazily, a list holding dozens of them', () => {
		const { root } = card({ imageUrl: 'https://lumia.test/cover.jpg' });
		expect(
			root.querySelector('img[src="https://lumia.test/cover.jpg"]')?.getAttribute('loading')
		).toBe('lazy');
	});
});
