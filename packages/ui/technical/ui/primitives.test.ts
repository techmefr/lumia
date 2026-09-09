import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import Card from './card.svelte';
import CardContent from './card-content.svelte';
import CardDescription from './card-description.svelte';
import CardFooter from './card-footer.svelte';
import CardHeader from './card-header.svelte';
import CardTitle from './card-title.svelte';
import Label from './label.svelte';
import Separator from './separator.svelte';
import Skeleton from './skeleton.svelte';

/**
 * These are wrappers: their whole job is to render one element, merge the caller's class over their
 * own defaults, and forward the rest. So that is what is asserted — anything more would be
 * asserting on the design.
 */
const WRAPPERS = [
	['Card', Card, 'DIV'],
	['CardHeader', CardHeader, 'DIV'],
	['CardTitle', CardTitle, 'DIV'],
	['CardDescription', CardDescription, 'DIV'],
	['CardContent', CardContent, 'DIV'],
	['CardFooter', CardFooter, 'DIV'],
	['Label', Label, 'LABEL']
] as const;

describe.each(WRAPPERS)('%s', (_name, Component, tag) => {
	function element(props: Record<string, unknown> = {}) {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const { container } = render(Component as any, props as any);
		return container.firstElementChild as HTMLElement;
	}

	it(`renders a single <${tag.toLowerCase()}>`, () => {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const { container } = render(Component as any, {} as any);
		expect(container.children).toHaveLength(1);
		expect(element().tagName).toBe(tag);
	});

	it('keeps the caller class alongside its own', () => {
		const node = element({ class: 'lumia-marker' });
		expect(node.className).toContain('lumia-marker');
	});

	it('forwards arbitrary attributes', () => {
		expect(element({ id: 'x', 'data-test-forwarded': 'yes' }).dataset.testForwarded).toBe('yes');
	});
});

describe('Skeleton', () => {
	function skeleton(props: Record<string, unknown> = {}) {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const { container } = render(Skeleton as any, props as any);
		return container.querySelector<HTMLElement>('[data-test-skeleton]')!;
	}

	// Decorative on purpose: the surrounding region announces the loading state once, and a screen
	// reader reading out every placeholder block would drown it.
	it('is hidden from assistive technology', () => {
		expect(skeleton().getAttribute('aria-hidden')).toBe('true');
	});

	it('animates while it waits', () => {
		expect(skeleton().className).toContain('animate-pulse');
	});

	it('takes the size the caller asks for', () => {
		expect(skeleton({ class: 'h-4 w-24' }).className).toContain('h-4');
	});
});

describe('Separator', () => {
	function separator(props: Record<string, unknown> = {}) {
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const { container } = render(Separator as any, props as any);
		return container.querySelector<HTMLElement>('[data-test-separator]')!;
	}

	// A rule between two groups is decoration, not content: bits-ui gives it the right role, and a
	// separator announced as a landmark would be noise on every settings page.
	it('carries the separator role', () => {
		expect(separator().getAttribute('role')).toBe('separator');
	});

	it('is horizontal unless asked otherwise', () => {
		expect(separator().getAttribute('data-orientation')).toBe('horizontal');
	});

	it('goes vertical when asked', () => {
		expect(separator({ orientation: 'vertical' }).getAttribute('data-orientation')).toBe('vertical');
	});

	// The two orientations need opposite one-pixel axes, so getting this wrong renders nothing at
	// all — a rule of zero height, invisible rather than obviously broken.
	it('is one pixel tall when horizontal and one pixel wide when vertical', () => {
		expect(separator().className).toContain('h-px');
		expect(separator({ orientation: 'vertical' }).className).toContain('w-px');
	});

	it('keeps the caller class', () => {
		expect(separator({ class: 'my-4' }).className).toContain('my-4');
	});
});
