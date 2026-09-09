import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import MagicBentoHarness from '../../test-support/magic-bento-harness.svelte';

type Props = Parameters<typeof MagicBentoHarness>[1];

function bento(props: Partial<Props> = {}) {
	const { container } = render(MagicBentoHarness, props as Props);
	const root = container.querySelector<HTMLElement>('[data-test-magic-bento]')!;
	const cell = (name: string) =>
		root.querySelector<HTMLElement>(`[data-test-cell="${name}"]`)!;

	// The cursor position is read from getBoundingClientRect, which jsdom always reports as a zero
	// box: without a stated geometry every computed offset would be zero and the test would pass on
	// a component that does nothing.
	function withBox(element: HTMLElement, box: { left: number; top: number; width: number; height: number }) {
		vi.spyOn(element, 'getBoundingClientRect').mockReturnValue({
			...box,
			right: box.left + box.width,
			bottom: box.top + box.height,
			x: box.left,
			y: box.top,
			toJSON: () => ({})
		} as DOMRect);
		return element;
	}

	return { root, cell, withBox };
}

const BOX = { left: 100, top: 200, width: 200, height: 100 };

describe('how it behaves as decoration', () => {
	// The grid adds layout and an ornament, no meaning: `presentation` keeps it out of the
	// accessibility tree while the cards inside stay in it.
	it('is presentational', () => {
		expect(bento().root.getAttribute('role')).toBe('presentation');
	});

	it('renders the cells it was given', () => {
		const view = bento();
		expect(view.cell('a')).not.toBeNull();
		expect(view.cell('b')).not.toBeNull();
	});

	it('uses the theme primary colour for the glow by default', () => {
		expect(bento().root.getAttribute('style')).toContain('var(--primary)');
	});

	it('uses the glow colour it was given', () => {
		expect(bento({ glowColor: 'rgb(204, 102, 51)' }).root.getAttribute('style')).toContain(
			'rgb(204, 102, 51)'
		);
	});

	it('keeps the caller class', () => {
		expect(bento({ class: 'lg:grid-cols-3' }).root.className).toContain('lg:grid-cols-3');
	});
});

describe('the spotlight', () => {
	it('follows the pointer inside the cell', async () => {
		const view = bento();
		const cell = view.withBox(view.cell('a'), BOX);

		await fireEvent.pointerMove(cell, { clientX: 150, clientY: 250 });

		expect(cell.style.getPropertyValue('--mx')).toBe('50px');
		expect(cell.style.getPropertyValue('--my')).toBe('50px');
	});

	// The pointer is almost never on the cell itself but on the text inside it, so the handler has
	// to walk up to the cell. Without that, the effect only fires in the gaps between children.
	it('finds the cell when the pointer is over a child of it', async () => {
		const view = bento();
		const cell = view.withBox(view.cell('a'), BOX);
		const inner = cell.querySelector<HTMLElement>('[data-test-inner]')!;

		await fireEvent.pointerMove(inner, { clientX: 300, clientY: 300 });

		expect(cell.style.getPropertyValue('--mx')).toBe('200px');
	});

	it('leaves a sibling cell untouched', async () => {
		const view = bento();
		const first = view.withBox(view.cell('a'), BOX);

		await fireEvent.pointerMove(first, { clientX: 150, clientY: 250 });

		expect(view.cell('b').style.getPropertyValue('--mx')).toBe('');
	});

	it('does nothing over content that is not a cell', async () => {
		const view = bento();
		const plain = view.root.querySelector<HTMLElement>('[data-test-plain]')!;

		await fireEvent.pointerMove(plain, { clientX: 150, clientY: 250 });

		expect(plain.style.getPropertyValue('--mx')).toBe('');
	});
});

describe('the tilt', () => {
	// The card leans away from the cursor: the sign is what makes it read as depth rather than as a
	// card sliding the wrong way, so both axes are pinned here.
	it('tilts away from the pointer at the top-left corner', async () => {
		const view = bento();
		const cell = view.withBox(view.cell('a'), BOX);

		await fireEvent.pointerMove(cell, { clientX: 100, clientY: 200 });

		expect(cell.style.getPropertyValue('--rx')).toBe('3.00deg');
		expect(cell.style.getPropertyValue('--ry')).toBe('-3.00deg');
	});

	it('tilts the other way at the bottom-right corner', async () => {
		const view = bento();
		const cell = view.withBox(view.cell('a'), BOX);

		await fireEvent.pointerMove(cell, { clientX: 300, clientY: 300 });

		expect(cell.style.getPropertyValue('--rx')).toBe('-3.00deg');
		expect(cell.style.getPropertyValue('--ry')).toBe('3.00deg');
	});

	it('lies flat at the centre', async () => {
		const view = bento();
		const cell = view.withBox(view.cell('a'), BOX);

		await fireEvent.pointerMove(cell, { clientX: 200, clientY: 250 });

		expect(cell.style.getPropertyValue('--rx')).toBe('0.00deg');
		expect(cell.style.getPropertyValue('--ry')).toBe('0.00deg');
	});

	// Without the reset the card stays frozen mid-tilt after the cursor leaves the grid, which
	// looks like a rendering bug rather than an effect.
	it('goes back to flat when the pointer leaves', async () => {
		const view = bento();
		const cell = view.withBox(view.cell('a'), BOX);

		await fireEvent.pointerMove(cell, { clientX: 300, clientY: 300 });
		await fireEvent.pointerLeave(view.root, { clientX: 300, clientY: 300 });

		expect(cell.style.getPropertyValue('--rx')).toBe('0deg');
		expect(cell.style.getPropertyValue('--ry')).toBe('0deg');
	});

	// `pointerleave` fires on the grid with the grid as its target, so a handler that walked up from
	// the target found no cell and left every card frozen mid-tilt. Flattening them all is both the
	// fix and the correct end state: the cursor is outside the grid by then.
	it('flattens every card, not only the one the pointer was on', async () => {
		const view = bento();
		const first = view.withBox(view.cell('a'), BOX);
		const second = view.withBox(view.cell('b'), BOX);

		await fireEvent.pointerMove(first, { clientX: 300, clientY: 300 });
		await fireEvent.pointerMove(second, { clientX: 100, clientY: 200 });
		await fireEvent.pointerLeave(view.root);

		expect(first.style.getPropertyValue('--rx')).toBe('0deg');
		expect(second.style.getPropertyValue('--rx')).toBe('0deg');
	});

	it('keeps the spotlight position on leave, so the glow fades where it was', async () => {
		const view = bento();
		const cell = view.withBox(view.cell('a'), BOX);

		await fireEvent.pointerMove(cell, { clientX: 150, clientY: 250 });
		await fireEvent.pointerLeave(view.root, { clientX: 150, clientY: 250 });

		expect(cell.style.getPropertyValue('--mx')).toBe('50px');
	});
});
