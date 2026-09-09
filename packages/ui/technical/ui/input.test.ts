import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import InputHarness from '../../test-support/input-harness.svelte';
import Input from './input.svelte';

type Props = Parameters<typeof Input>[1];

function input(props: Partial<Props> = {}) {
	const { container } = render(Input, props as Props);
	return container.querySelector<HTMLInputElement>('[data-test-input]')!;
}

describe('the rendered input', () => {
	it('renders an input element', () => {
		expect(input().tagName).toBe('INPUT');
	});

	it('shows the value it was given', () => {
		expect(input({ value: 'svelte' }).value).toBe('svelte');
	});

	it('sets the type it was given', () => {
		expect(input({ type: 'search' } as Props).type).toBe('search');
	});

	// No `type` at all rather than a hardcoded `text`: the html default is already text, and forcing
	// it would stop a caller from binding `type` reactively.
	it('sets no type attribute when none is asked for', () => {
		expect(input().hasAttribute('type')).toBe(false);
	});

	it('forwards the placeholder', () => {
		expect(input({ placeholder: 'Search articles' } as Props).placeholder).toBe('Search articles');
	});

	it('forwards the disabled state', () => {
		expect(input({ disabled: true } as Props).disabled).toBe(true);
	});

	it('forwards accessibility attributes', () => {
		const element = input({ 'aria-label': 'Search', required: true } as Props);
		expect(element.getAttribute('aria-label')).toBe('Search');
		expect(element.required).toBe(true);
	});

	it('merges the caller class with its own', () => {
		const element = input({ class: 'max-w-xs' });
		expect(element.className).toContain('max-w-xs');
		expect(element.className).toContain('rounded-md');
	});

	it('lets the caller class win over a conflicting default', () => {
		const element = input({ class: 'h-12' });
		expect(element.className).toContain('h-12');
		expect(element.className).not.toContain('h-9');
	});
});

describe('what the caller can bind', () => {
	// Observed through a parent harness rather than by reaching into the component: `$bindable`
	// props are not exports, so being the parent is the only place a binding is visible at all.
	it('hands back the underlying element through ref', () => {
		const { container } = render(InputHarness);
		expect(container.querySelector('[data-test-ref-tag]')?.textContent).toBe('INPUT');
	});

	it('reports what the user typed through value', async () => {
		const { container } = render(InputHarness);
		const element = container.querySelector<HTMLInputElement>('[data-test-input]')!;

		await fireEvent.input(element, { target: { value: 'rss' } });

		expect(container.querySelector('[data-test-bound-value]')?.textContent).toBe('rss');
	});
});
