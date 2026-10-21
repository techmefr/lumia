import { afterEach, describe, expect, it, vi } from 'vitest';
import { prefersReducedMotion, scrollBehavior } from './motion';

function stubReducedMotion(matches: boolean) {
	vi.stubGlobal('matchMedia', (query: string) => ({
		matches: matches && query.includes('prefers-reduced-motion'),
		media: query
	}));
}

describe('motion preference', () => {
	afterEach(() => vi.unstubAllGlobals());

	it('scrolls smoothly when the user has no motion preference', () => {
		stubReducedMotion(false);
		expect(prefersReducedMotion()).toBe(false);
		expect(scrollBehavior()).toBe('smooth');
	});

	it('jumps instead of gliding when the user asked for reduced motion', () => {
		stubReducedMotion(true);
		expect(prefersReducedMotion()).toBe(true);
		expect(scrollBehavior()).toBe('auto');
	});
});
