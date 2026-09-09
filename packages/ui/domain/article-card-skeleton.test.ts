import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ArticleCardSkeleton from './article-card-skeleton.svelte';

type Props = Parameters<typeof ArticleCardSkeleton>[1];

function skeleton(props: Partial<Props> = {}) {
	const { container } = render(ArticleCardSkeleton, props as Props);
	const root = container.querySelector<HTMLElement>('[data-test-article-card-skeleton]')!;
	return {
		root,
		blocks: () => [...root.querySelectorAll<HTMLElement>('[data-test-skeleton]')],
		band: () => root.querySelector<HTMLElement>('[data-test-skeleton]')!
	};
}

describe('what it announces', () => {
	// Hidden on purpose: the list around it owns the loading announcement, and reading out six
	// placeholder blocks per card would bury it.
	it('is hidden from assistive technology', () => {
		expect(skeleton().root.getAttribute('aria-hidden')).toBe('true');
	});

	it('contains no text a screen reader could read out', () => {
		expect(skeleton().root.textContent?.trim()).toBe('');
	});
});

describe('what it draws', () => {
	it('stands in for the image band and the four lines of the card', () => {
		expect(skeleton().blocks()).toHaveLength(5);
	});

	it('animates every block, so it reads as loading rather than as empty', () => {
		for (const block of skeleton().blocks()) {
			expect(block.className).toContain('animate-pulse');
		}
	});
});

describe('the featured variant', () => {
	// The point of the variant: the placeholder has to occupy exactly what the real card will, or
	// the grid reflows the moment the data lands and everything the reader was looking at moves.
	it('matches the tall image band of a featured card', () => {
		expect(skeleton({ featured: true }).band().className).toContain('h-64');
		expect(skeleton().band().className).toContain('h-36');
	});

	it('spans two columns like the featured card it stands in for', () => {
		expect(skeleton({ featured: true }).root.className).toContain('sm:col-span-2');
		expect(skeleton().root.className).not.toContain('sm:col-span-2');
	});
});

describe('the caller class', () => {
	it('is kept alongside the component defaults', () => {
		expect(skeleton({ class: 'opacity-50' }).root.className).toContain('opacity-50');
	});
});
