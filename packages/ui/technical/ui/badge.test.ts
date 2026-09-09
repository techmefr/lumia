import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import Badge from './badge.svelte';
import { badgeVariants } from './badge.svelte.js';

type Props = Parameters<typeof Badge>[1];

function badge(props: Partial<Props> = {}) {
	const { container } = render(Badge, props as Props);
	return container.querySelector('span')!;
}

const VARIANTS = ['default', 'secondary', 'outline', 'destructive'] as const;

describe('the variant table', () => {
	it('falls back to the default variant', () => {
		expect(badgeVariants()).toBe(badgeVariants({ variant: 'default' }));
	});

	it.each(VARIANTS)('gives the %s variant its own class string', (variant) => {
		const others = VARIANTS.filter((other) => other !== variant).map((other) =>
			badgeVariants({ variant: other })
		);

		expect(others).not.toContain(badgeVariants({ variant }));
	});

	it.each(VARIANTS)('carries the shared base into the %s variant', (variant) => {
		expect(badgeVariants({ variant })).toContain('inline-flex');
	});
});

describe('the rendered badge', () => {
	// A badge is a label, not a region: an element with a role would be announced as one more thing
	// to navigate on a card that already has plenty.
	it('renders a plain span', () => {
		expect(badge().tagName).toBe('SPAN');
	});

	it('merges the caller class with the variant classes', () => {
		const element = badge({ class: 'ml-2' });
		expect(element.className).toContain('ml-2');
		expect(element.className).toContain('inline-flex');
	});

	it('lets the caller class win over a conflicting default', () => {
		const element = badge({ class: 'rounded-full' });
		expect(element.className).toContain('rounded-full');
		expect(element.className).not.toContain('rounded-md');
	});

	it('forwards arbitrary attributes', () => {
		expect(badge({ title: '12 unread' } as Props).getAttribute('title')).toBe('12 unread');
	});
});
