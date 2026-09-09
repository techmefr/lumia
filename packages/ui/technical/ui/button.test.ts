import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import Button from './button.svelte';
import { buttonVariants } from './button.svelte.js';

type Props = Parameters<typeof Button>[1];

function button(props: Partial<Props> = {}) {
	const { container } = render(Button, props as Props);
	return {
		anchor: container.querySelector('a'),
		element: container.querySelector('a, button')!
	};
}

// The variant table is a pure function from props to a class string: the string *is* its output,
// so asserting on it is not asserting on styling — it is the only observable this module has.
describe('the variant table', () => {
	it('applies the default variant and size when neither is asked for', () => {
		expect(buttonVariants()).toBe(buttonVariants({ variant: 'default', size: 'default' }));
	});

	it.each(['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const)(
		'gives the %s variant its own class string',
		(variant) => {
			const others = (['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'] as const)
				.filter((other) => other !== variant)
				.map((other) => buttonVariants({ variant: other }));

			expect(others).not.toContain(buttonVariants({ variant }));
		}
	);

	it.each(['default', 'sm', 'lg', 'icon'] as const)(
		'gives the %s size its own class string',
		(size) => {
			const others = (['default', 'sm', 'lg', 'icon'] as const)
				.filter((other) => other !== size)
				.map((other) => buttonVariants({ size: other }));

			expect(others).not.toContain(buttonVariants({ size }));
		}
	);

	it('carries the shared base into every variant', () => {
		for (const variant of ['default', 'destructive', 'outline', 'secondary', 'ghost'] as const) {
			expect(buttonVariants({ variant })).toContain('inline-flex');
		}
	});
});

describe('which element it renders', () => {
	it('renders a button when no href is given', () => {
		expect(button().element.tagName).toBe('BUTTON');
	});

	it('renders an anchor to the href it was given', () => {
		const { element } = button({ href: '/articles' });
		expect(element.tagName).toBe('A');
		expect(element.getAttribute('href')).toBe('/articles');
	});

	// `disabled` has no meaning on an anchor: the link stays clickable and keyboard-focusable, so a
	// "disabled" link would still navigate. Rendering a real disabled button is the fix, and this is
	// the case that keeps it.
	it('renders a real disabled button rather than a dead link', () => {
		const { element, anchor } = button({ href: '/articles', disabled: true });
		expect(anchor).toBeNull();
		expect(element.tagName).toBe('BUTTON');
		expect((element as HTMLButtonElement).disabled).toBe(true);
	});
});

describe('the attributes it forwards', () => {
	it('defaults the type to button, so it never submits a form by accident', () => {
		expect(button().element.getAttribute('type')).toBe('button');
	});

	it('keeps an explicit submit type', () => {
		expect(button({ type: 'submit' }).element.getAttribute('type')).toBe('submit');
	});

	it('sets no type on the anchor form', () => {
		expect(button({ href: '/x' }).element.hasAttribute('type')).toBe(false);
	});

	it('forwards arbitrary attributes such as aria-label', () => {
		expect(button({ 'aria-label': 'Close' } as Props).element.getAttribute('aria-label')).toBe(
			'Close'
		);
	});

	// Nested under `props` because `target` is also one of testing-library's own render options:
	// passed flat it would be read as "where to mount" instead of as a prop.
	it('forwards them on the anchor form too', () => {
		const { container } = render(Button, {
			props: { href: '/x', target: '_blank' }
		} as Parameters<typeof render>[1]);
		expect(container.querySelector('a')?.getAttribute('target')).toBe('_blank');
	});

	it('merges the caller class with the variant classes', () => {
		const { element } = button({ class: 'w-full' });
		expect(element.className).toContain('w-full');
		expect(element.className).toContain('inline-flex');
	});

	// This is what `cn` is for at the component boundary: a caller has to be able to override a
	// default, not merely add a class that loses on source order.
	it('lets the caller class win over a conflicting default', () => {
		const { element } = button({ size: 'lg', class: 'h-20' });
		expect(element.className).toContain('h-20');
		expect(element.className).not.toContain('h-10');
	});
});
