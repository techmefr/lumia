import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import BorderGlow from './border-glow.svelte';

type Props = Parameters<typeof BorderGlow>[1];

function glow(props: Partial<Props> = {}) {
	const { container } = render(BorderGlow, props as Props);
	return container.querySelector<HTMLElement>('[data-test-border-glow]')!;
}

describe('how it behaves as decoration', () => {
	// Three properties make an ornament safe to drop behind a card: it is not announced, it does not
	// eat the click meant for the link underneath, and it sits below its content.
	it('is hidden from assistive technology', () => {
		expect(glow().getAttribute('aria-hidden')).toBe('true');
	});

	it('lets pointer events through to the card it decorates', () => {
		expect(glow().className).toContain('pointer-events-none');
	});

	it('sits behind its content', () => {
		expect(glow().className).toContain('-z-10');
	});

	it('carries no text of its own', () => {
		expect(glow().textContent).toBe('');
	});
});

describe('when it shows', () => {
	it('is visible by default', () => {
		expect(glow().className).toContain('opacity-70');
		expect(glow().className).not.toContain('opacity-0');
	});

	// The opt-out for a dense list, where one glow per row is noise: the ornament then only appears
	// on the row under the cursor.
	it('waits for hover when alwaysOn is off', () => {
		const node = glow({ alwaysOn: false });
		expect(node.className).toContain('opacity-0');
		expect(node.className).toContain('group-hover:opacity-70');
	});
});

describe('what the caller can tune', () => {
	it('uses the theme primary colour by default', () => {
		expect(glow().getAttribute('style')).toContain('var(--primary)');
	});

	// Stated in rgb because jsdom's cssom normalises whatever notation goes in, so an hsl literal
	// would come back out as rgb and the assertion would be about the parser, not the component.
	it('uses the colour it was given', () => {
		expect(glow({ color: 'rgb(204, 102, 51)' }).getAttribute('style')).toContain(
			'rgb(204, 102, 51)'
		);
	});

	it('spins over four seconds by default', () => {
		expect(glow().getAttribute('style')).toContain('4s');
	});

	it('spins at the speed it was given', () => {
		expect(glow({ speed: 12 }).getAttribute('style')).toContain('12s');
	});

	it('keeps the caller class', () => {
		expect(glow({ class: 'rounded-full' }).className).toContain('rounded-full');
	});
});
