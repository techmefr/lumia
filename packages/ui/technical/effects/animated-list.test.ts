import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import AnimatedListHarness from '../../test-support/animated-list-harness.svelte';

type Props = Parameters<typeof AnimatedListHarness>[1];

const ITEMS = [
	{ id: 'a', label: 'Actualités' },
	{ id: 'b', label: 'Bricolage' },
	{ id: 'c', label: 'Cuisine' }
];

function list(props: Partial<Props> = {}) {
	const { container, rerender } = render(AnimatedListHarness, { items: ITEMS, ...props } as Props);
	const root = container.querySelector<HTMLElement>('[data-test-animated-list]')!;
	return {
		root,
		rerender,
		rows: () => [...root.querySelectorAll<HTMLElement>('[data-test-animated-item]')],
		labels: () =>
			[...root.querySelectorAll<HTMLElement>('[data-test-item]')].map((node) => node.textContent),
		delays: () =>
			[...root.querySelectorAll<HTMLElement>('[data-test-animated-item]')].map(
				(node) => node.style.animationDelay
			)
	};
}

describe('what it renders', () => {
	it('renders one row per item, in order', () => {
		expect(list().labels()).toEqual(['Actualités', 'Bricolage', 'Cuisine']);
	});

	it('renders nothing but the container for an empty list', () => {
		const view = list({ items: [] });
		expect(view.root).not.toBeNull();
		expect(view.rows()).toHaveLength(0);
	});

	it('hands the snippet the index of each item', () => {
		const indexes = [...list().root.querySelectorAll<HTMLElement>('[data-test-item]')].map(
			(node) => node.dataset.testIndex
		);
		expect(indexes).toEqual(['0', '1', '2']);
	});

	it('keeps the caller class on the container', () => {
		expect(list({ class: 'px-2' }).root.className).toContain('px-2');
	});
});

describe('the stagger', () => {
	// The whole point of the component: rows cascade instead of appearing all at once. The delay is
	// a per-row style, so it is observable without waiting for anything.
	it('delays each row a little more than the one before', () => {
		expect(list().delays()).toEqual(['0ms', '40ms', '80ms']);
	});

	it('honours a stagger the caller asks for', () => {
		expect(list({ staggerMs: 100 }).delays()).toEqual(['0ms', '100ms', '200ms']);
	});

	// Zero is the escape hatch for a long list, where forty milliseconds per row means the last one
	// arrives seconds late.
	it('mounts everything at once when the stagger is zero', () => {
		expect(list({ staggerMs: 0 }).delays()).toEqual(['0ms', '0ms', '0ms']);
	});
});

describe('keying', () => {
	// Without a key svelte keys by index, so removing the first item re-uses its dom node for the
	// second and the entry animation replays on rows that never moved.
	it('keeps the same dom node for an item that survives a reorder', async () => {
		const view = list({ getKey: (item) => item.id });
		const cuisine = view.root.querySelector('[data-test-item="c"]');

		await view.rerender({ items: [ITEMS[2], ITEMS[0], ITEMS[1]], getKey: (item) => item.id });

		expect(view.root.querySelector('[data-test-item="c"]')).toBe(cuisine);
		expect(view.labels()).toEqual(['Cuisine', 'Actualités', 'Bricolage']);
	});

	it('falls back to the index when no key is given', async () => {
		const view = list();
		await view.rerender({ items: [ITEMS[2]] });
		expect(view.labels()).toEqual(['Cuisine']);
	});
});
