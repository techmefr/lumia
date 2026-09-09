import { render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { manualFrames, recordingCanvasContext } from '../../test-support/recording-canvas.js';
import ClickSpark from './click-spark.svelte';

type Props = Parameters<typeof ClickSpark>[1];

/**
 * The media query is the outer boundary here, and jsdom implements no `matchMedia` at all — so it
 * has to be provided for the component to run, and stating its answer is what lets the
 * reduced-motion branch be tested.
 */
function prefersReducedMotion(reduce: boolean) {
	vi.stubGlobal(
		'matchMedia',
		(query: string) =>
			({
				matches: reduce && query.includes('prefers-reduced-motion'),
				media: query,
				onchange: null,
				addEventListener: () => {},
				removeEventListener: () => {},
				addListener: () => {},
				removeListener: () => {},
				dispatchEvent: () => false
			}) as MediaQueryList
	);
}

function spark(props: Partial<Props> = {}) {
	const view = render(ClickSpark, props as Props);
	return {
		...view,
		canvas: view.container.querySelector<HTMLCanvasElement>('[data-test-click-spark]')!
	};
}

beforeEach(() => {
	prefersReducedMotion(false);
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
});

describe('the canvas it draws on', () => {
	// It covers the whole viewport at all times, so the two properties that matter are that it is
	// invisible to assistive technology and completely transparent to the pointer — otherwise it
	// would swallow every click in the app.
	it('is hidden from assistive technology', () => {
		expect(spark().canvas.getAttribute('aria-hidden')).toBe('true');
	});

	it('lets every click through to the app underneath', () => {
		expect(spark().canvas.className).toContain('pointer-events-none');
	});

	it('covers the viewport without joining the layout', () => {
		const { canvas } = spark();
		expect(canvas.className).toContain('fixed');
		expect(canvas.style.width).toBe('100vw');
	});

	it('keeps the caller class on the wrapper without adding a box', () => {
		// `contents` on purpose: the wrapper must not become a grid item or a flex child of
		// whatever it is dropped into.
		const { container } = render(ClickSpark, { class: 'lumia-marker' } as Props);
		const wrapper = container.querySelector('.contents')!;
		expect(wrapper.className).toContain('lumia-marker');
	});
});

describe('sizing itself to the window', () => {
	it('matches the viewport on mount', () => {
		prefersReducedMotion(false);
		const { canvas } = spark();
		expect(canvas.width).toBe(window.innerWidth);
		expect(canvas.height).toBe(window.innerHeight);
	});

	it('follows the window when it is resized', () => {
		prefersReducedMotion(false);
		const { canvas } = spark();

		vi.stubGlobal('innerWidth', 640);
		window.dispatchEvent(new Event('resize'));

		expect(canvas.width).toBe(640);
	});

	// A listener left on the window after unmount keeps writing to a canvas nobody can see, once
	// per resize, for the life of the page.
	it('stops following the window once unmounted', () => {
		prefersReducedMotion(false);
		const { canvas, unmount } = spark();
		const sizeBefore = canvas.width;

		unmount();
		vi.stubGlobal('innerWidth', sizeBefore + 320);
		window.dispatchEvent(new Event('resize'));

		expect(canvas.width).toBe(sizeBefore);
	});
});

describe('respecting prefers-reduced-motion', () => {
	// The animation runs on requestAnimationFrame against a canvas, where the global
	// prefers-reduced-motion css block cannot reach it. So the component has to check the query
	// itself, and this is the case that proves it still does.
	it('never starts the animation loop', () => {
		prefersReducedMotion(true);
		const frame = vi.spyOn(window, 'requestAnimationFrame');

		spark();

		expect(frame).not.toHaveBeenCalled();
		frame.mockRestore();
	});

	// 300 is the html default for a canvas nobody has sized: the component never touched it.
	it('leaves the canvas alone rather than sizing it to the window', () => {
		prefersReducedMotion(true);
		expect(spark().canvas.width).toBe(300);
	});

	it('still renders the canvas, so the layout is identical either way', () => {
		prefersReducedMotion(true);
		expect(spark().canvas).not.toBeNull();
	});
});

describe('clicking', () => {
	it('does not consume the click it decorates', () => {
		spark();

		const event = new MouseEvent('click', {
			clientX: 40,
			clientY: 60,
			bubbles: true,
			cancelable: true
		});
		document.body.dispatchEvent(event);

		expect(event.defaultPrevented).toBe(false);
	});

	it('stops handling clicks once unmounted', () => {
		const { unmount } = spark();
		unmount();

		expect(() =>
			document.body.dispatchEvent(new MouseEvent('click', { clientX: 1, clientY: 1, bubbles: true }))
		).not.toThrow();
	});
});

describe('the sparks it draws', () => {
	function click(x = 100, y = 100) {
		document.body.dispatchEvent(new MouseEvent('click', { clientX: x, clientY: y, bubbles: true }));
	}

	function scene(props: Partial<Props> = {}) {
		const recording = recordingCanvasContext();
		const frames = manualFrames();
		vi.spyOn(performance, 'now').mockReturnValue(0);
		const view = spark(props);
		return { ...view, recording, frames };
	}

	it('draws nothing until something is clicked', () => {
		const { recording, frames } = scene();
		frames.step(0);
		expect(recording.lines).toHaveLength(0);
	});

	it('draws one line per spark on the next frame', () => {
		const { recording, frames } = scene();
		click();
		frames.step(10);
		expect(recording.lines).toHaveLength(8);
	});

	it('draws as many sparks as asked for', () => {
		const { recording, frames } = scene({ sparkCount: 3 });
		click();
		frames.step(10);
		expect(recording.lines).toHaveLength(3);
	});

	// Evenly spread around the click, which is what makes it read as a burst rather than as a
	// direction: eight sparks at 45° apart put exactly two on each axis of the compass.
	it('spreads the sparks evenly around the click', () => {
		const { recording, frames } = scene({ sparkCount: 4, sparkRadius: 20 });
		click(100, 100);
		frames.step(175);

		const angles = recording.lines
			.map(({ from }) => Math.round((Math.atan2(from[1] - 100, from[0] - 100) * 180) / Math.PI))
			.sort((a, b) => a - b);
		expect(angles).toEqual([-90, 0, 90, 180]);
	});

	it('clears the canvas each frame rather than smearing the trail', () => {
		const { recording, frames } = scene();
		click();
		frames.step(10);
		frames.step(20);
		expect(recording.clears).toBe(2);
	});

	// A spark travels outwards and shortens as it goes, so it fades by shrinking to nothing at the
	// end of its life instead of vanishing at full length.
	it('moves each spark outwards and shortens it as it ages', () => {
		const { recording, frames } = scene({ sparkCount: 1, duration: 100, sparkRadius: 40 });
		click(100, 100);

		frames.step(10);
		frames.step(80);

		const [early, late] = recording.lines;
		expect(late.from[0]).toBeGreaterThan(early.from[0]);
		expect(late.to[0] - late.from[0]).toBeLessThan(early.to[0] - early.from[0]);
	});

	it('drops a spark once its duration is up', () => {
		const { recording, frames } = scene({ duration: 100 });
		click();

		frames.step(50);
		const drawnWhileAlive = recording.lines.length;
		frames.step(100);

		expect(drawnWhileAlive).toBe(8);
		expect(recording.lines).toHaveLength(8);
	});

	it('keeps animating for later clicks after an earlier burst has expired', () => {
		const { recording, frames } = scene({ duration: 100 });
		click();
		frames.step(150);
		expect(recording.lines).toHaveLength(0);

		vi.spyOn(performance, 'now').mockReturnValue(150);
		click();
		frames.step(160);
		expect(recording.lines).toHaveLength(8);
	});

	it.each(['linear', 'ease-in', 'ease-out', 'ease-in-out'] as const)(
		'travels on the %s curve',
		(easing) => {
			const { recording, frames } = scene({ easing, sparkCount: 1, duration: 100, sparkRadius: 40 });
			click(100, 100);
			frames.step(25);
			expect(recording.lines[0].from[0]).toBeGreaterThanOrEqual(100);
		}
	);

	// Each easing has to actually change the trajectory, or the prop is decoration.
	it('gives each easing a trajectory of its own', () => {
		const positions = (['linear', 'ease-in', 'ease-out', 'ease-in-out'] as const).map((easing) => {
			const { recording, frames } = scene({ easing, sparkCount: 1, duration: 100, sparkRadius: 40 });
			click(100, 100);
			frames.step(25);
			const position = recording.lines[0].from[0];
			vi.restoreAllMocks();
			return position;
		});

		expect(new Set(positions).size).toBe(positions.length);
	});

	it('reaches further when the extra scale is turned up', () => {
		function distanceAt(extraScale: number) {
			const { recording, frames } = scene({
				sparkCount: 1,
				duration: 100,
				sparkRadius: 40,
				extraScale
			});
			click(100, 100);
			frames.step(50);
			const distance = recording.lines[0].from[0] - 100;
			vi.restoreAllMocks();
			return distance;
		}

		expect(distanceAt(3)).toBeGreaterThan(distanceAt(1));
	});

	it('strokes in the colour it was given', () => {
		const { recording, frames } = scene({ sparkColor: 'rgb(255, 0, 0)' });
		click();
		frames.step(10);
		expect(recording.lines[0].color).toBe('rgb(255, 0, 0)');
	});

	// A canvas cannot resolve a css variable, so the component resolves it against the document
	// first, through a throwaway probe element. jsdom's cssom does not resolve custom properties
	// either — it echoes the `var()` back — so what a real browser hands the stroke cannot be
	// asserted here; what can is that the probe path runs, strokes, and leaves nothing behind.
	it('goes through the document to resolve a theme token, and cleans up after itself', () => {
		const { recording, frames } = scene({ sparkColor: 'var(--primary)' });
		click();
		frames.step(10);

		expect(recording.lines).toHaveLength(8);
		expect(document.body.querySelector('span')).toBeNull();
	});

	it('stops the loop when it unmounts', () => {
		const { frames, unmount } = scene();
		unmount();
		expect(frames.cancelled).toBe(true);
	});
});
