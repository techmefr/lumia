import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import GradualBlur from './gradual-blur.svelte';

type Props = Parameters<typeof GradualBlur>[1];

// Read through the cssom rather than off the style attribute: jsdom re-serialises what it parses,
// so a substring match on the raw string would be a test of its whitespace conventions.
//
// Props are nested under `props` because this component has one called `target`, which is also
// testing-library's own option for where to mount: passed flat it would be read as a mount target.
function blur(props: Partial<Props> = {}) {
	const { container } = render(GradualBlur, { props } as Parameters<typeof render>[1]);
	const root = container.querySelector<HTMLElement>('[data-test-gradual-blur]')!;
	const layers = () => [...root.querySelectorAll<HTMLElement>('[data-test-blur-layer]')];
	return {
		root,
		layers,
		radii: () =>
			layers().map((node) => {
				const match = /blur\(([\d.]+)rem\)/.exec(node.style.getPropertyValue('backdrop-filter'));
				return match ? Number(match[1]) : Number.NaN;
			})
	};
}

describe('how it behaves as decoration', () => {
	// It sits over real content — the bottom of a scrolling article — so it must neither be
	// announced nor swallow a tap on the text beneath it.
	it('is hidden from assistive technology', () => {
		expect(blur().root.getAttribute('aria-hidden')).toBe('true');
	});

	it('lets pointer events through', () => {
		expect(blur().root.style.pointerEvents).toBe('none');
	});

	it('keeps the caller class', () => {
		expect(blur({ class: 'rounded-b-2xl' }).root.className).toContain('rounded-b-2xl');
	});
});

describe('the stack of layers', () => {
	// The gradient is faked by stacking masked layers, each blurrier than the last: a single
	// backdrop-filter can only have one radius, so the count is the resolution of the ramp.
	it('draws five layers by default', () => {
		expect(blur().layers()).toHaveLength(5);
	});

	it('draws as many layers as asked for', () => {
		expect(blur({ divCount: 9 }).layers()).toHaveLength(9);
	});

	it('draws a single layer without falling over', () => {
		expect(blur({ divCount: 1 }).layers()).toHaveLength(1);
	});

	it('gets blurrier layer by layer', () => {
		const radii = blur().radii();
		expect(radii).toEqual([...radii].sort((a, b) => a - b));
		expect(new Set(radii).size).toBe(radii.length);
	});

	it('scales every radius with the strength', () => {
		const soft = blur({ strength: 1 }).radii();
		const hard = blur({ strength: 4 }).radii();
		expect(hard.every((value, index) => value > soft[index])).toBe(true);
	});

	// The exponential ramp exists for a tall fade, where a linear one still reads as five distinct
	// bands: it puts almost all the blur in the last layers instead of spreading it evenly.
	it('back-loads the blur when asked to go exponential', () => {
		const linear = blur({ curve: 'linear' }).radii();
		const exponential = blur({ exponential: true }).radii();
		expect(exponential[0]).toBeLessThan(linear[0]);
		expect(exponential[exponential.length - 1]).toBeGreaterThan(linear[linear.length - 1]);
	});

	it.each(['linear', 'bezier', 'ease-in', 'ease-out', 'ease-in-out'] as const)(
		'ramps monotonically on the %s curve',
		(curve) => {
			const radii = blur({ curve }).radii();
			expect(radii).toEqual([...radii].sort((a, b) => a - b));
		}
	);

	it('gives each curve a ramp of its own', () => {
		const shapes = (['linear', 'bezier', 'ease-in', 'ease-out'] as const).map((curve) =>
			blur({ curve }).radii().join('|')
		);
		expect(new Set(shapes).size).toBe(shapes.length);
	});

	// An unknown curve name is a typo, not a reason to render nothing.
	it('falls back to linear for a curve it does not know', () => {
		const unknown = blur({ curve: 'wobble' as Props['curve'] }).radii();
		expect(unknown).toEqual(blur({ curve: 'linear' }).radii());
	});

	it('applies the opacity to every layer', () => {
		for (const layer of blur({ opacity: 0.5 }).layers()) {
			expect(layer.style.opacity).toBe('0.5');
		}
	});

	// Safari still needs the prefixed mask, and a fade that only works in Chrome is a fade half the
	// readers never see. Only the mask can be asserted: jsdom's cssom drops
	// `-webkit-backdrop-filter` outright, so its presence is not observable here.
	it('ships the webkit-prefixed mask alongside the standard one', () => {
		const layer = blur().layers()[0];
		expect(layer.style.getPropertyValue('-webkit-mask-image')).toContain('linear-gradient');
		expect(layer.style.getPropertyValue('mask-image')).toContain('linear-gradient');
	});
});

describe('where it sits', () => {
	it.each(['top', 'bottom'] as const)('takes a fixed height along the %s edge', (position) => {
		const { root } = blur({ position, height: '8rem' });
		expect(root.style.height).toBe('8rem');
		expect(root.style.width).toBe('100%');
		expect(root.style.getPropertyValue(position)).toBe('0px');
	});

	// On a side edge, `height` is the thickness of the band: the prop keeps its name so a caller
	// does not have to think about which axis it is on.
	it.each(['left', 'right'] as const)(
		'takes its thickness from height on the %s edge',
		(position) => {
			const { root } = blur({ position, height: '8rem' });
			expect(root.style.width).toBe('8rem');
			expect(root.style.height).toBe('100%');
			expect(root.style.getPropertyValue(position)).toBe('0px');
		}
	);

	it('prefers an explicit width over the thickness derived from height', () => {
		expect(blur({ position: 'left', height: '8rem', width: '2rem' }).root.style.width).toBe('2rem');
	});

	it('masks towards the edge it is pinned to', () => {
		expect(blur({ position: 'top' }).layers()[0].style.getPropertyValue('mask-image')).toContain(
			'linear-gradient(to top'
		);
		expect(blur({ position: 'right' }).layers()[0].style.getPropertyValue('mask-image')).toContain(
			'linear-gradient(to right'
		);
	});
});

describe('what it is anchored to', () => {
	it('is absolute inside its parent by default', () => {
		expect(blur().root.style.position).toBe('absolute');
	});

	it('is fixed to the viewport when targeting the page', () => {
		expect(blur({ target: 'page' }).root.style.position).toBe('fixed');
	});

	// A page-level fade has to clear whatever the page stacks over its own content, so it gets a
	// deliberate boost rather than the caller having to guess a z-index.
	it('stacks a page fade above a parent one', () => {
		expect(blur({ zIndex: 30 }).root.style.zIndex).toBe('30');
		expect(blur({ zIndex: 30, target: 'page' }).root.style.zIndex).toBe('130');
	});
});
