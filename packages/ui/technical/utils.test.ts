import { describe, expect, it } from 'vitest';
import { cn } from './utils';

describe('cn', () => {
	it('joins several class strings', () => {
		expect(cn('rounded-md', 'border')).toBe('rounded-md border');
	});

	it('drops a falsy branch, so a conditional class can be written inline', () => {
		expect(cn('border', false && 'hidden', undefined, null)).toBe('border');
	});

	it('flattens an array', () => {
		expect(cn(['border', 'p-2'])).toBe('border p-2');
	});

	it('keeps only the last of two conflicting tailwind utilities', () => {
		expect(cn('p-2', 'p-4')).toBe('p-4');
	});

	// This is the whole point of the helper: a caller's `class` prop has to be able to override the
	// component's own default, not merely sit next to it and lose on source order.
	it('lets a caller override a component default', () => {
		expect(cn('bg-card text-sm', 'bg-transparent')).toBe('text-sm bg-transparent');
	});

	it('resolves conflicts per axis, leaving unrelated utilities alone', () => {
		expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
	});

	it('returns an empty string when given nothing', () => {
		expect(cn()).toBe('');
	});

	it('handles the object form', () => {
		expect(cn({ border: true, hidden: false })).toBe('border');
	});
});
