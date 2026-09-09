import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import ReadingProgress from './reading-progress.svelte';

type Props = Parameters<typeof ReadingProgress>[1];

function bar(props: Partial<Props>) {
	const { container } = render(ReadingProgress, { progress: 0, ...props } as Props);
	const root = container.querySelector('[role="progressbar"]')!;
	return {
		root,
		valuenow: () => Number(root.getAttribute('aria-valuenow')),
		width: () => container.querySelector<HTMLElement>('[data-test-progress-bar]')!.style.width
	};
}

describe('the announced value', () => {
	it.each([
		[0, 0],
		[0.005, 1],
		[0.25, 25],
		[0.5, 50],
		[0.999, 100],
		[1, 100]
	])('turns a progress of %s into %i percent', (progress, expected) => {
		expect(bar({ progress }).valuenow()).toBe(expected);
	});

	// A scroll container can report slightly past either end — a rubber-band bounce on iOS, a
	// rounding error on a short article. Clamping keeps the announced value inside the range the
	// aria contract promises rather than announcing 104%.
	it.each([-1, -0.4, 0])('clamps %s to zero', (progress) => {
		expect(bar({ progress }).valuenow()).toBe(0);
	});

	it.each([1, 1.2, 12])('clamps %s to a hundred', (progress) => {
		expect(bar({ progress }).valuenow()).toBe(100);
	});

	it('declares the range it is announcing against', () => {
		const { root } = bar({ progress: 0.5 });
		expect(root.getAttribute('aria-valuemin')).toBe('0');
		expect(root.getAttribute('aria-valuemax')).toBe('100');
	});
});

describe('the visible track', () => {
	it('matches the announced percentage, so sighted and screen reader users see the same thing', () => {
		expect(bar({ progress: 0.42 }).width()).toBe('42%');
	});

	it('is empty at the start', () => {
		expect(bar({ progress: 0 }).width()).toBe('0%');
	});

	it('is full at the end', () => {
		expect(bar({ progress: 1 }).width()).toBe('100%');
	});

	it('never overflows the track when progress does', () => {
		expect(bar({ progress: 3 }).width()).toBe('100%');
	});
});

describe('the label', () => {
	// The package ships no translations: the app owns those. The default only exists so the bar is
	// never unlabelled when a caller forgets.
	it('falls back to an english default', () => {
		expect(bar({ progress: 0 }).root.getAttribute('aria-label')).toBe('Reading progress');
	});

	it('uses the label the app passes in', () => {
		expect(bar({ progress: 0, label: 'Progression de lecture' }).root.getAttribute('aria-label')).toBe(
			'Progression de lecture'
		);
	});
});
