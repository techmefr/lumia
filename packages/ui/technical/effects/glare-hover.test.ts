import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import GlareHover from './glare-hover.svelte';

type Props = Parameters<typeof GlareHover>[1];

function glare(props: Partial<Props> = {}) {
	const { container } = render(GlareHover, props as Props);
	const root = container.querySelector<HTMLElement>('[data-test-glare]')!;
	const overlay = container.querySelector<HTMLElement>('[data-test-glare-overlay]')!;
	return {
		root,
		overlay,
		enter: () => fireEvent.mouseEnter(root),
		leave: () => fireEvent.mouseLeave(root)
	};
}

describe('how it behaves as decoration', () => {
	// It wraps content it knows nothing about, so it must add no meaning: `presentation` keeps the
	// wrapper out of the accessibility tree while its children stay in it.
	it('is presentational', () => {
		expect(glare().root.getAttribute('role')).toBe('presentation');
	});

	it('lets pointer events through to whatever it covers', () => {
		expect(glare().overlay.style.pointerEvents).toBe('none');
	});

	it('clips the sweep to its own box', () => {
		expect(glare().root.className).toContain('overflow-hidden');
	});

	it('keeps the caller class', () => {
		expect(glare({ class: 'absolute inset-0' }).root.className).toContain('inset-0');
	});
});

describe('the glare colour', () => {
	// The colour arrives as a hex string and has to come out as rgba, because the opacity is a
	// separate prop and hex has nowhere to put it.
	it('turns a six-digit hex into rgba at the given opacity', () => {
		const { overlay } = glare({ glareColor: '#3366cc', glareOpacity: 0.4 });
		expect(overlay.style.background).toContain('rgba(51, 102, 204, 0.4)');
	});

	it('expands a three-digit hex the same way', () => {
		const { overlay } = glare({ glareColor: '#36c', glareOpacity: 0.4 });
		expect(overlay.style.background).toContain('rgba(51, 102, 204, 0.4)');
	});

	it('is white at half opacity by default', () => {
		expect(glare().overlay.style.background).toContain('rgba(255, 255, 255, 0.5)');
	});

	// Anything that is not a hex triple goes through untouched for css to resolve — a theme token,
	// a named colour, or a typo. Opacity is then that value's business, not ours. A named colour is
	// what the assertion uses because jsdom's cssom discards a declaration it cannot parse, so
	// `var(--primary)` or a malformed hex leaves nothing in the dom to look at; all three take the
	// identical branch.
	it('passes a non-hex colour straight through', () => {
		const { overlay } = glare({ glareColor: 'rebeccapurple' });
		expect(overlay.style.background).toContain('rebeccapurple');
	});

	it('uses the angle it was given', () => {
		expect(glare({ glareAngle: 30 }).overlay.style.background).toContain('linear-gradient(30deg');
	});

	it('uses the size it was given, on both axes', () => {
		expect(glare({ glareSize: 300 }).overlay.style.backgroundSize).toContain('300% 300%');
	});
});

describe('the sweep', () => {
	// Off-canvas at rest is the whole reason the effect is invisible until hovered. A regression
	// here shows up as a permanent white streak across every card.
	it('parks the glare outside the box at rest', () => {
		expect(glare().overlay.style.backgroundPosition).toBe('-100% -100%, 0px 0px');
	});

	it('sweeps across on hover', async () => {
		const view = glare();
		await view.enter();
		expect(view.overlay.style.backgroundPosition).toBe('100% 100%, 0px 0px');
	});

	it('sweeps back out when the pointer leaves', async () => {
		const view = glare();
		await view.enter();
		await view.leave();
		expect(view.overlay.style.backgroundPosition).toBe('-100% -100%, 0px 0px');
	});

	it('animates the sweep over the duration it was given', async () => {
		const view = glare({ transitionDuration: 900 });
		await view.enter();
		expect(view.overlay.style.transition).toBe('900ms ease');
	});

	// playOnce snaps back instead of sweeping in reverse: the return sweep reads as a second
	// deliberate highlight, which is exactly what a one-shot effect must not do.
	it('snaps back without a reverse sweep when it plays once', async () => {
		const view = glare({ playOnce: true });
		await view.enter();
		await view.leave();
		expect(view.overlay.style.transition).toBe('none');
		expect(view.overlay.style.backgroundPosition).toBe('-100% -100%, 0px 0px');
	});

	it('replays from the start on a second hover', async () => {
		const view = glare();
		await view.enter();
		await view.leave();
		await view.enter();
		expect(view.overlay.style.backgroundPosition).toBe('100% 100%, 0px 0px');
	});
});

describe('the box it draws', () => {
	it('fills its container by default', () => {
		const { root } = glare();
		expect(root.style.width).toBe('100%');
		expect(root.style.height).toBe('100%');
	});

	it('takes the size, radius and background it was given', () => {
		const { root } = glare({
			width: '20rem',
			height: '10rem',
			borderRadius: '1rem',
			background: 'rgb(255, 0, 0)'
		});
		expect(root.style.width).toBe('20rem');
		expect(root.style.height).toBe('10rem');
		expect(root.style.borderRadius).toBe('1rem');
		expect(root.style.background).toContain('rgb(255, 0, 0)');
	});

	it('appends the caller style after its own', () => {
		expect(glare({ style: 'opacity:0.5;' }).root.style.opacity).toBe('0.5');
	});
});
