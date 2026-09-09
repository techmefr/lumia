import { describe, expect, it } from 'vitest';
import { accentHueForFeed } from './accent-hue';

// The curated set the module documents. Restated here rather than imported: a test that reads the
// same constant as the code cannot notice the constant changing.
const SAFE_HUES = [220, 35, 175, 265, 320, 200, 15, 245];

describe('accentHueForFeed', () => {
	it('gives the same feed the same hue every time', () => {
		expect(accentHueForFeed('feed-atelier-papier')).toBe(accentHueForFeed('feed-atelier-papier'));
	});

	it('only ever returns a hue from the colourblind-safe set', () => {
		const hues = new Set<number>();
		for (let index = 0; index < 500; index += 1) {
			hues.add(accentHueForFeed(`feed-${index}`));
		}
		expect([...hues].every((hue) => SAFE_HUES.includes(hue))).toBe(true);
	});

	it('spreads across the whole set rather than collapsing onto one hue', () => {
		const hues = new Set<number>();
		for (let index = 0; index < 500; index += 1) {
			hues.add(accentHueForFeed(`feed-${index}`));
		}
		expect(hues.size).toBe(SAFE_HUES.length);
	});

	it('separates two ids that differ only in their last character', () => {
		expect(accentHueForFeed('feed-a')).not.toBe(accentHueForFeed('feed-b'));
	});

	it('handles an empty id instead of returning undefined', () => {
		expect(SAFE_HUES).toContain(accentHueForFeed(''));
	});

	it('does not overflow on an id long enough to wrap the hash', () => {
		const hue = accentHueForFeed('x'.repeat(5000));
		expect(SAFE_HUES).toContain(hue);
		expect(Number.isInteger(hue)).toBe(true);
	});
});
