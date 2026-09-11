import type { ArticleSummary } from '@lumia/core';
import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import FlipReader from './flip-reader.svelte';

type Props = Parameters<typeof FlipReader>[1];

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

function reader(props: Partial<Props> = {}) {
	const onClose = vi.fn();
	const onPage = vi.fn();
	const { container } = render(FlipReader, {
		articles: THREE,
		onClose,
		onPage,
		...props
	} as Props);

	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		onClose,
		onPage,
		counter: () => q('[data-test-flip-counter]')!,
		close: () => q<HTMLButtonElement>('[data-test-flip-close]')!,
		prev: () => q<HTMLButtonElement>('[data-test-flip-prev]')!,
		next: () => q<HTMLButtonElement>('[data-test-flip-next]')!,
		open: () => q<HTMLAnchorElement>('[data-test-flip-open]'),
		stage: () => q('[data-test-flip-stage]'),
		empty: () => q('[data-test-flip-empty]'),
		title: () => q('h2')
	};
}

describe('turning pages', () => {
	it('opens on the requested article', () => {
		const view = reader({ startIndex: 1 });
		expect(view.title()?.textContent).toBe('Titre b');
		expect(view.counter().textContent?.trim()).toBe('2 / 3');
	});

	it('moves forward and reports the new page', async () => {
		const view = reader({ startIndex: 0 });

		await fireEvent.click(view.next());

		expect(view.title()?.textContent).toBe('Titre b');
		expect(view.onPage).toHaveBeenCalledWith(1);
	});

	it('moves backward', async () => {
		const view = reader({ startIndex: 2 });

		await fireEvent.click(view.prev());

		expect(view.title()?.textContent).toBe('Titre b');
	});

	it('disables previous on the first page', () => {
		const view = reader({ startIndex: 0 });
		expect(view.prev().disabled).toBe(true);
	});

	it('disables next on the last page', () => {
		const view = reader({ startIndex: 2 });
		expect(view.next().disabled).toBe(true);
	});

	it('does not go past either end', async () => {
		const view = reader({ startIndex: 2 });

		await fireEvent.click(view.next());

		expect(view.title()?.textContent).toBe('Titre c');
		expect(view.onPage).not.toHaveBeenCalled();
	});

	it('moves with the arrow keys', async () => {
		const view = reader({ startIndex: 0 });

		await fireEvent.keyDown(window, { key: 'ArrowRight' });

		expect(view.title()?.textContent).toBe('Titre b');
	});

	it('moves with j and k too', async () => {
		const view = reader({ startIndex: 1 });

		await fireEvent.keyDown(window, { key: 'k' });
		expect(view.title()?.textContent).toBe('Titre a');

		await fireEvent.keyDown(window, { key: 'j' });
		expect(view.title()?.textContent).toBe('Titre b');
	});

	it('clamps a start index past the end of a shorter list', () => {
		const view = reader({ articles: [article('solo')], startIndex: 5 });
		expect(view.title()?.textContent).toBe('Titre solo');
	});
});

describe('focus management', () => {
	it('moves focus into the dialog when it opens', () => {
		const trigger = document.createElement('button');
		document.body.appendChild(trigger);
		trigger.focus();

		reader();

		expect(document.activeElement?.getAttribute('data-test-flip-close')).not.toBeNull();
		trigger.remove();
	});

	it('keeps Tab from leaving the dialog', async () => {
		const view = reader({ startIndex: 0 });

		view.close().focus();
		await fireEvent.keyDown(view.close(), { key: 'Tab', shiftKey: true });

		expect(document.activeElement).toBe(view.next());
	});

	it('returns focus to what was focused before opening, once closed', async () => {
		const trigger = document.createElement('button');
		document.body.appendChild(trigger);
		trigger.focus();

		const { unmount } = render(FlipReader, {
			articles: THREE,
			onClose: vi.fn(),
			onPage: vi.fn()
		} as Props);
		unmount();

		expect(document.activeElement).toBe(trigger);
		trigger.remove();
	});

	it('announces the current page to screen readers when it changes', async () => {
		const view = reader({ startIndex: 0 });
		const live = view.container.querySelector('[aria-live="polite"]');

		await fireEvent.click(view.next());

		expect(live?.textContent).toContain('Titre b');
	});
});

describe('closing', () => {
	it('closes on the close button', async () => {
		const view = reader();

		await fireEvent.click(view.close());

		expect(view.onClose).toHaveBeenCalledOnce();
	});

	it('closes on escape', async () => {
		const view = reader();

		await fireEvent.keyDown(window, { key: 'Escape' });

		expect(view.onClose).toHaveBeenCalledOnce();
	});
});

describe('an empty list', () => {
	it('shows the empty state instead of a page', () => {
		const view = reader({ articles: [] });
		expect(view.empty()).not.toBeNull();
		expect(view.stage()).toBeNull();
		expect(view.counter().textContent?.trim()).toBe('0 / 0');
	});
});

describe('reading the current article', () => {
	it('links to the full article', () => {
		const view = reader({ startIndex: 0 });
		expect(view.open()?.getAttribute('href')).toBe('/articles/a');
	});

	it('shows the summary when there is one', () => {
		const view = reader({ articles: [article('a', { summary: 'Un resume court.' })] });
		expect(view.container.textContent).toContain('Un resume court.');
	});

	it('shows no relevance badge at the neutral score', () => {
		const view = reader({ articles: [article('a', { relevance_score: 50 })] });
		expect(view.container.textContent).not.toContain('50/100');
	});

	it('shows the relevance badge once it moves off neutral', () => {
		const view = reader({ articles: [article('a', { relevance_score: 74 })] });
		expect(view.container.textContent).toContain('74/100');
	});
});
