import { describe, expect, it } from 'vitest';
import { safeHttpHref } from './safe-href';

describe('safeHttpHref', () => {
	it('keeps http and https urls', () => {
		expect(safeHttpHref('https://blog.test/a')).toBe('https://blog.test/a');
		expect(safeHttpHref('http://blog.test/a')).toBe('http://blog.test/a');
	});

	it('refuses javascript:, data: and relative values', () => {
		expect(safeHttpHref('javascript:alert(1)')).toBeUndefined();
		expect(safeHttpHref('data:text/html,x')).toBeUndefined();
		expect(safeHttpHref('/relative')).toBeUndefined();
	});

	it('refuses an empty value', () => {
		expect(safeHttpHref('')).toBeUndefined();
		expect(safeHttpHref(null)).toBeUndefined();
	});
});
