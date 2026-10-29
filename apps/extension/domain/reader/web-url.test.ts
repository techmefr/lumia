import { describe, expect, it } from 'vitest';
import { isWebUrl } from './web-url';

describe('isWebUrl', () => {
	it('accepts http and https', () => {
		expect(isWebUrl('https://a.test/x')).toBe(true);
		expect(isWebUrl('http://a.test')).toBe(true);
	});

	it('refuses scripts, data, relative and empty values', () => {
		expect(isWebUrl('javascript:alert(1)')).toBe(false);
		expect(isWebUrl('data:text/html,x')).toBe(false);
		expect(isWebUrl('/relative')).toBe(false);
		expect(isWebUrl('')).toBe(false);
		expect(isWebUrl(null)).toBe(false);
	});
});
