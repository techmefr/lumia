import { afterEach, describe, expect, it } from 'vitest';
import { stripQueryParam } from './strip-query-param';

afterEach(() => window.history.replaceState(null, '', '/'));

describe('stripQueryParam', () => {
	it('removes the named parameter and keeps the others', () => {
		window.history.replaceState(null, '', '/login?magic_token=secret&next=1#x');

		stripQueryParam('magic_token');

		expect(window.location.search).toBe('?next=1');
		expect(window.location.hash).toBe('#x');
	});

	it('leaves the url alone when the parameter is absent', () => {
		window.history.replaceState(null, '', '/login?next=1');

		stripQueryParam('magic_token');

		expect(window.location.search).toBe('?next=1');
	});
});
