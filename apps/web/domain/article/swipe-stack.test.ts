import type { ArticleSummary } from '@lumia/core';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SwipeStack from './swipe-stack.svelte';

type Props = Parameters<typeof SwipeStack>[1];

const COMMIT_MS = 250;

function article(id: string, overrides: Partial<ArticleSummary> = {}): ArticleSummary {
	return {
		id,
		title: `Titre ${id}`,
		summary: null,
		url: `https://example.test/${id}`,
		image_url: null,
		source_label: 'Atelier Papier',
		feed_id: 'feed-1',
		author_id: null,
		author_name: null,
		category_id: null,
		category_name: null,
		published_at: '2026-08-09T08:30:00Z',
		reading_minutes: 4,
		read: false,
		scroll_progress: 0,
		relevance_score: 50,
		...overrides
	};
}

const THREE = [article('a'), article('b'), article('c')];

function stack(props: Partial<Props> = {}) {
	const onLike = vi.fn();
	const onDislike = vi.fn();
	const onSave = vi.fn();
	const onFavorite = vi.fn();
	const onOpen = vi.fn();
	const { container, unmount } = render(SwipeStack, {
		articles: THREE,
		onLike,
		onDislike,
		onSave,
		onFavorite,
		onOpen,
		...props
	} as Props);

	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		unmount,
		onLike,
		onDislike,
		onSave,
		onFavorite,
		onOpen,
		card: () => q('[data-test-swipe-card]'),
		title: () => q('h2'),
		open: () => q<HTMLButtonElement>('[data-test-swipe-open]')!,
		like: () => q<HTMLButtonElement>('[data-test-swipe-like]')!,
		dislike: () => q<HTMLButtonElement>('[data-test-swipe-dislike]')!,
		save: () => q<HTMLButtonElement>('[data-test-swipe-save]')!,
		favorite: () => q<HTMLButtonElement>('[data-test-swipe-favorite]')!,
		remaining: () => q('[aria-live="polite"]'),
		scroll: () => q<HTMLElement>('[data-test-swipe-scroll]'),
		expand: () => q<HTMLButtonElement>('[data-test-swipe-expand]')!,
		hint: () => q('[data-test-swipe-hint]'),
		heroClasses: () => q<HTMLElement>('h2')!.parentElement!.parentElement!.className
	};
}

// jsdom implements the pointer events themselves but not pointer capture, and swipe-stack calls
// `setPointerCapture` on every drag start — a browser api at the outer boundary, stubbed the same
// way `Element.prototype.animate` is stubbed elsewhere.
beforeEach(() => {
	Element.prototype.setPointerCapture = vi.fn();
	vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
	vi.useRealTimers();
});

async function settle() {
	vi.advanceTimersByTime(COMMIT_MS);
	await Promise.resolve();
}

describe('the buttons', () => {
	it('likes the current article and advances the stack', async () => {
		const view = stack();

		await fireEvent.click(view.like());
		await settle();

		expect(view.onLike).toHaveBeenCalledWith(THREE[0]);
		expect(view.title()?.textContent).toBe('Titre b');
	});

	it('dislikes the current article', async () => {
		const view = stack();

		await fireEvent.click(view.dislike());
		await settle();

		expect(view.onDislike).toHaveBeenCalledWith(THREE[0]);
	});

	it('saves the current article', async () => {
		const view = stack();

		await fireEvent.click(view.save());
		await settle();

		expect(view.onSave).toHaveBeenCalledWith(THREE[0]);
	});

	it('favorites the current article', async () => {
		const view = stack();

		await fireEvent.click(view.favorite());
		await settle();

		expect(view.onFavorite).toHaveBeenCalledWith(THREE[0]);
	});

	it('opens the current article', async () => {
		const view = stack();

		await fireEvent.click(view.open());

		expect(view.onOpen).toHaveBeenCalledWith(THREE[0]);
	});
});

describe('working through the stack', () => {
	it('empties out and renders nothing once every article is gone', async () => {
		const view = stack({ articles: [article('solo')] });

		await fireEvent.click(view.like());
		await settle();

		expect(view.card()).toBeNull();
	});

	it('announces the title and how many are left, for a screen reader', () => {
		const view = stack();
		expect(view.remaining()?.textContent).toContain('Titre a');
		expect(view.remaining()?.textContent).toContain('3');
	});

	it('does not act twice on the same article once it is exiting', async () => {
		const view = stack();

		await fireEvent.click(view.like());
		await fireEvent.click(view.dislike());
		await settle();

		expect(view.onLike).toHaveBeenCalledOnce();
		expect(view.onDislike).not.toHaveBeenCalled();
	});
});

describe('the keyboard alternative to swiping', () => {
	it('likes on ArrowRight', async () => {
		const view = stack();

		await fireEvent.keyDown(document, { key: 'ArrowRight' });
		await settle();

		expect(view.onLike).toHaveBeenCalledWith(THREE[0]);
	});

	it('dislikes on ArrowLeft', async () => {
		const view = stack();

		await fireEvent.keyDown(document, { key: 'ArrowLeft' });
		await settle();

		expect(view.onDislike).toHaveBeenCalledWith(THREE[0]);
	});

	it('favorites on ArrowUp', async () => {
		const view = stack();

		await fireEvent.keyDown(document, { key: 'ArrowUp' });
		await settle();

		expect(view.onFavorite).toHaveBeenCalledWith(THREE[0]);
	});

	it('saves for later on ArrowDown', async () => {
		const view = stack();

		await fireEvent.keyDown(document, { key: 'ArrowDown' });
		await settle();

		expect(view.onSave).toHaveBeenCalledWith(THREE[0]);
	});

	it('does not act twice when the key repeats while the card is already exiting', async () => {
		const view = stack();

		await fireEvent.keyDown(document, { key: 'ArrowRight' });
		await fireEvent.keyDown(document, { key: 'ArrowLeft' });
		await settle();

		expect(view.onLike).toHaveBeenCalledOnce();
		expect(view.onDislike).not.toHaveBeenCalled();
	});

	it('documents the keyboard alternative on screen', () => {
		const view = stack();

		expect(view.hint()?.textContent?.trim().length).toBeGreaterThan(0);
	});

	it('stops reacting to the keyboard once the component is destroyed', async () => {
		const view = stack();
		view.unmount();

		await fireEvent.keyDown(document, { key: 'ArrowRight' });
		await settle();

		expect(view.onLike).not.toHaveBeenCalled();
	});
});

describe('dragging the card', () => {
	function drag(card: Element, from: [number, number], to: [number, number]) {
		fireEvent.pointerDown(card, { clientX: from[0], clientY: from[1], button: 0 });
		fireEvent.pointerMove(card, { clientX: to[0], clientY: to[1] });
		return fireEvent.pointerUp(card, { clientX: to[0], clientY: to[1] });
	}

	it('opens the article on a quick tap that barely moves', async () => {
		const view = stack();

		await drag(view.card()!, [100, 100], [102, 101]);

		expect(view.onOpen).toHaveBeenCalledWith(THREE[0]);
	});

	it('likes on a firm rightward drag', async () => {
		const view = stack();

		await drag(view.card()!, [100, 100], [300, 100]);
		await settle();

		expect(view.onLike).toHaveBeenCalledWith(THREE[0]);
	});

	it('dislikes on a firm leftward drag', async () => {
		const view = stack();

		await drag(view.card()!, [300, 100], [80, 100]);
		await settle();

		expect(view.onDislike).toHaveBeenCalledWith(THREE[0]);
	});

	it('favorites on a firm upward drag', async () => {
		const view = stack();

		await drag(view.card()!, [100, 300], [100, 80]);
		await settle();

		expect(view.onFavorite).toHaveBeenCalledWith(THREE[0]);
	});

	it('saves for later on a firm downward drag', async () => {
		const view = stack();

		await drag(view.card()!, [100, 80], [100, 300]);
		await settle();

		expect(view.onSave).toHaveBeenCalledWith(THREE[0]);
	});

	it('does nothing on a drag that falls short of the threshold', async () => {
		const view = stack();

		await drag(view.card()!, [100, 100], [140, 100]);
		await settle();

		expect(view.onLike).not.toHaveBeenCalled();
		expect(view.onDislike).not.toHaveBeenCalled();
		expect(view.onOpen).not.toHaveBeenCalled();
	});
});

describe('reading the article inside the card', () => {
	const LONG = 'Paragraphe. '.repeat(80);
	const WITH_SUMMARY = [article('long', { summary: LONG }), article('next', { summary: LONG })];

	it('shows the whole summary in a scrollable region instead of truncating it', () => {
		const view = stack({ articles: WITH_SUMMARY });

		const scroll = view.scroll()!;
		expect(scroll.textContent?.trim()).toBe(LONG.trim());
		expect(scroll.className).toContain('overflow-y-auto');
	});

	it('keeps that region reachable with the keyboard', () => {
		const view = stack({ articles: WITH_SUMMARY });

		const scroll = view.scroll()!;
		expect(scroll.getAttribute('tabindex')).toBe('0');
		expect(scroll.getAttribute('aria-labelledby')).toBe('swipe-title-long');
	});

	it('gives the text more room when the reader unfolds the card', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		expect(view.expand().getAttribute('aria-expanded')).toBe('false');
		expect(view.heroClasses()).toContain('h-56');

		await fireEvent.click(view.expand());

		expect(view.expand().getAttribute('aria-expanded')).toBe('true');
		expect(view.heroClasses()).toContain('h-24');
	});

	it('does not read a click on an in-card button as a tap on the card', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		fireEvent.pointerDown(view.expand(), { clientX: 10, clientY: 10, button: 0 });
		await fireEvent.pointerUp(view.expand(), { clientX: 10, clientY: 10 });

		expect(view.onOpen).not.toHaveBeenCalled();
	});

	it('folds back when the stack advances to the next article', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		await fireEvent.click(view.expand());
		await fireEvent.click(view.like());
		await settle();

		expect(view.expand().getAttribute('aria-expanded')).toBe('false');
	});
});

describe('scrolling the text rather than swiping the card', () => {
	const LONG = 'Paragraphe. '.repeat(80);
	const WITH_SUMMARY = [article('long', { summary: LONG }), article('next', { summary: LONG })];

	function dragFrom(target: Element, from: [number, number], to: [number, number]) {
		fireEvent.pointerDown(target, { clientX: from[0], clientY: from[1], button: 0 });
		fireEvent.pointerMove(target, { clientX: to[0], clientY: to[1] });
		return fireEvent.pointerUp(target, { clientX: to[0], clientY: to[1] });
	}

	it('does not favorite when the reader scrolls up inside the text', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		await dragFrom(view.scroll()!, [100, 300], [100, 60]);
		await settle();

		expect(view.onFavorite).not.toHaveBeenCalled();
		expect(view.onSave).not.toHaveBeenCalled();
		expect(view.onOpen).not.toHaveBeenCalled();
	});

	it('does not save for later when the reader scrolls down inside the text', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		await dragFrom(view.scroll()!, [100, 60], [100, 300]);
		await settle();

		expect(view.onSave).not.toHaveBeenCalled();
		expect(view.onFavorite).not.toHaveBeenCalled();
	});

	it('leaves the card where it was after a vertical scroll gesture', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		await dragFrom(view.scroll()!, [100, 300], [100, 60]);

		expect(view.card()?.getAttribute('style')).toContain('translate(0px, 0px)');
	});

	it('still likes on a horizontal drag that starts inside the text', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		await dragFrom(view.scroll()!, [100, 100], [320, 130]);
		await settle();

		expect(view.onLike).toHaveBeenCalledWith(WITH_SUMMARY[0]);
	});

	it('ignores a mostly vertical drag even when it drifts sideways', async () => {
		const view = stack({ articles: WITH_SUMMARY });

		await dragFrom(view.scroll()!, [100, 300], [160, 60]);
		await settle();

		expect(view.onLike).not.toHaveBeenCalled();
		expect(view.onDislike).not.toHaveBeenCalled();
		expect(view.onFavorite).not.toHaveBeenCalled();
	});
});
