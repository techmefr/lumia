import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ArticleHero from './article-hero.svelte';

type Props = Parameters<typeof ArticleHero>[1];

const BASE = {
	id: 'article-7',
	href: '/articles/article-7',
	title: 'Le papier revient par la fenêtre',
	sourceLabel: 'Atelier Papier',
	publishedAt: '2026-08-09T08:30:00Z',
	accentHue: 220
} satisfies Partial<Props>;

// Selectors are data-test-* rather than classes: the classes here exist for visual reasons and
// change on a design pass, which must not be able to take the suite down with it.
function hero(overrides: Partial<Props> = {}) {
	const { container } = render(ArticleHero, { ...BASE, ...overrides } as Props);
	const root = container.querySelector('[data-test-article-hero]')!;
	return {
		root,
		title: () => root.querySelector('[data-test-article-title]'),
		summary: () => root.querySelector('[data-test-article-summary]'),
		source: () => root.querySelector('[data-test-source-label]'),
		avatar: () => root.querySelector('[data-test-source-avatar]'),
		icon: () => root.querySelector<HTMLImageElement>('[data-test-source-icon]'),
		image: () => root.querySelector<HTMLImageElement>('[data-test-article-image]'),
		date: () => root.querySelector('[data-test-published-date]'),
		readLabel: () => root.querySelector('[data-test-read-label]'),
		minutes: () => root.querySelector('[data-test-reading-minutes]'),
		score: () => root.querySelector('[data-test-relevance-score]'),
		cta: () => root.querySelector('[data-test-cta]'),
		glow: () => root.querySelector('[data-test-border-glow]')
	};
}

describe('what the hero always shows', () => {
	it('carries the article id, so the page can be addressed by article', () => {
		expect(hero().root.getAttribute('data-test-article-hero')).toBe('article-7');
	});

	it('links to the article', () => {
		expect(hero().root.getAttribute('href')).toBe('/articles/article-7');
	});

	it('shows the title', () => {
		expect(hero().title()?.textContent?.trim()).toBe(BASE.title);
	});

	it('shows the source', () => {
		expect(hero().source()?.textContent?.trim()).toBe('Atelier Papier');
	});

	// The heading is the article's, not the page's: the hero sits under the app's own h1.
	it('marks the title as a heading', () => {
		expect(hero().title()?.tagName).toBe('H2');
	});

	it('shows a decorative border glow that assistive technology ignores', () => {
		expect(hero().glow()?.getAttribute('aria-hidden')).toBe('true');
	});
});

describe('the summary', () => {
	it('is shown when there is one', () => {
		expect(hero({ summary: 'Une enquête sur les kiosques.' }).summary()?.textContent?.trim()).toBe(
			'Une enquête sur les kiosques.'
		);
	});

	it.each([null, undefined, ''])('renders nothing at all for %p', (summary) => {
		expect(hero({ summary }).summary()).toBeNull();
	});
});

describe('the date', () => {
	it('is formatted in the locale the app passes in', () => {
		expect(hero({ locale: 'fr' }).date()?.textContent).toContain('9 août');
	});

	it('follows the locale rather than hardcoding one', () => {
		expect(hero({ locale: 'en' }).date()?.textContent).toContain('August 9');
	});
});

describe('the read state', () => {
	it('is not announced on an unread article', () => {
		expect(hero().readLabel()).toBeNull();
		expect(hero().root.getAttribute('data-test-read')).toBe('false');
	});

	it('is announced on a read one', () => {
		const view = hero({ read: true, readLabel: 'lu' });
		expect(view.root.getAttribute('data-test-read')).toBe('true');
		expect(view.readLabel()?.textContent).toContain('lu');
	});

	// Dimmed, never hidden: a read article stays reachable, and hover brings it back to full
	// contrast so the text is still readable while you are on it.
	it('dims a read article without removing it', () => {
		expect(hero({ read: true }).root.className).toContain('opacity-70');
		expect(hero().root.className).not.toContain('opacity-70');
	});
});

describe('the reading time', () => {
	it('is shown, formatted by the app', () => {
		const view = hero({ readingMinutes: 7, minutesLabel: (minutes) => `${minutes} min de lecture` });
		expect(view.minutes()?.textContent?.trim()).toBe('7 min de lecture');
	});

	it.each([null, undefined, 0])('is not shown for %p', (readingMinutes) => {
		expect(hero({ readingMinutes }).minutes()).toBeNull();
	});
});

describe('the relevance score', () => {
	it('is shown when the score says something', () => {
		expect(hero({ relevanceScore: 87 }).score()?.textContent).toContain('87');
	});

	// 50 is the neutral score every article starts on. Showing it would put a meaningless badge on
	// every single article, which is the same as showing nothing while looking like a signal.
	it('is hidden at the neutral value of fifty', () => {
		expect(hero({ relevanceScore: 50 }).score()).toBeNull();
	});

	it.each([null, undefined])('is hidden for %p', (relevanceScore) => {
		expect(hero({ relevanceScore }).score()).toBeNull();
	});

	it('is shown at both ends of the scale', () => {
		expect(hero({ relevanceScore: 0 }).score()?.textContent).toContain('0');
		expect(hero({ relevanceScore: 100 }).score()?.textContent).toContain('100');
	});

	// The number alone means nothing read out of context, so the unit is in the accessible name.
	it('spells out what the number means for a screen reader', () => {
		const view = hero({ relevanceScore: 87, scoreSuffix: 'sur 100 de pertinence' });
		expect(view.score()?.textContent).toContain('sur 100 de pertinence');
	});

	it('carries the tooltip the app passes in', () => {
		const view = hero({ relevanceScore: 87, scoreTitle: 'Score de pertinence' });
		expect(view.score()?.getAttribute('title')).toBe('Score de pertinence');
	});
});

describe('the images', () => {
	it('shows the article image when there is one', () => {
		expect(hero({ imageUrl: 'https://example.test/a.jpg' }).image()?.src).toBe(
			'https://example.test/a.jpg'
		);
	});

	// Decorative: the title next to it already says what the article is.
	it('gives the article image an empty alt', () => {
		expect(hero({ imageUrl: 'https://example.test/a.jpg' }).image()?.getAttribute('alt')).toBe('');
	});

	it('shows no image element when there is no image', () => {
		expect(hero().image()).toBeNull();
	});

	// A hotlinked image from a feed dies routinely — the origin moves it, or blocks the referrer.
	// Falling back to the tinted gradient keeps the layout intact instead of leaving a broken icon.
	it('falls back to the gradient when the image fails to load', async () => {
		const view = hero({ imageUrl: 'https://example.test/gone.jpg' });
		await fireEvent.error(view.image()!);
		expect(view.image()).toBeNull();
	});

	it('shows the source icon when there is one', () => {
		expect(hero({ iconUrl: 'https://example.test/i.png' }).icon()?.src).toBe(
			'https://example.test/i.png'
		);
	});

	it('falls back to the source initial when there is no icon', () => {
		expect(hero().avatar()?.textContent?.trim()).toBe('A');
	});

	it('falls back to the initial when the icon fails to load', async () => {
		const view = hero({ iconUrl: 'https://example.test/gone.png' });
		await fireEvent.error(view.icon()!);
		expect(view.avatar()?.textContent?.trim()).toBe('A');
	});

	it('upper-cases the initial whatever the source name looks like', () => {
		expect(hero({ sourceLabel: 'le monde' }).avatar()?.textContent?.trim()).toBe('L');
	});
});

describe('the call to action', () => {
	it('falls back to an english default', () => {
		expect(hero().cta()?.textContent?.trim()).toBe('Read the lead →');
	});

	it('uses the label the app passes in', () => {
		expect(hero({ ctaLabel: 'Lire la une →' }).cta()?.textContent?.trim()).toBe('Lire la une →');
	});
});

describe('the shared view transition', () => {
	// The name has to match the card's for the image to fly from the list into the article. If the
	// two ever drift apart the transition silently degrades to a cross-fade.
	it('names the image band after the article, so it can morph from the card', () => {
		const band = hero().root.querySelector<HTMLElement>('[style*="view-transition-name"]')!;
		expect(band.style.getPropertyValue('view-transition-name')).toBe('article-image-article-7');
	});
});

describe('the caller class', () => {
	it('is kept alongside the component defaults', () => {
		expect(hero({ class: 'mb-8' }).root.className).toContain('mb-8');
	});
});
