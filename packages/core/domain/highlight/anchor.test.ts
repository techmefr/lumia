import { describe, expect, it } from 'vitest';
import { ANCHOR_CONTEXT_LENGTH, buildAnchor, locateAnchor } from './anchor';

const TEXT = 'Sur le papier et l encre, le papier compte. Le papier reste.';

describe('building an anchor', () => {
	it('keeps the passage, its offsets and the text around it', () => {
		const anchor = buildAnchor(TEXT, { start: 4, end: 13 });

		expect(anchor).toEqual({
			quote: 'le papier',
			prefix: 'Sur ',
			suffix: ' et l encre, le papier compte. L',
			start_offset: 4,
			end_offset: 13
		});
	});

	it('caps the context on both sides', () => {
		const long = 'a'.repeat(100) + 'QUOTE' + 'b'.repeat(100);

		const anchor = buildAnchor(long, { start: 100, end: 105 });

		expect(anchor.prefix).toBe('a'.repeat(ANCHOR_CONTEXT_LENGTH));
		expect(anchor.suffix).toBe('b'.repeat(ANCHOR_CONTEXT_LENGTH));
	});

	it('has an empty prefix at the very start and an empty suffix at the very end', () => {
		const anchor = buildAnchor('abc', { start: 0, end: 3 });

		expect(anchor.prefix).toBe('');
		expect(anchor.suffix).toBe('');
	});
});

describe('locating an anchor', () => {
	it('trusts the stored offset while it still lands on the quote', () => {
		const anchor = buildAnchor(TEXT, { start: 26, end: 35 });

		expect(locateAnchor(TEXT, anchor)).toEqual({ start: 26, end: 35 });
	});

	it('finds the passage again when the text before it has shifted', () => {
		const anchor = buildAnchor(TEXT, { start: 26, end: 35 });
		const shifted = `Chapeau ajouté. ${TEXT}`;

		expect(locateAnchor(shifted, anchor)).toEqual({ start: 42, end: 51 });
	});

	it('picks the occurrence whose surroundings match when the quote repeats', () => {
		const anchor = buildAnchor(TEXT, { start: 26, end: 35 });
		const shifted = `Préface. ${TEXT}`;

		expect(locateAnchor(shifted, anchor)).toEqual({ start: 35, end: 44 });
	});

	it('falls back on the occurrence nearest the old offset when the context ties', () => {
		const anchor = { quote: 'x', prefix: '', suffix: '', start_offset: 12, end_offset: 13 };

		expect(locateAnchor('x...........abc..x', anchor)).toEqual({ start: 17, end: 18 });
	});

	it('reports a passage that is gone instead of guessing', () => {
		const anchor = buildAnchor(TEXT, { start: 4, end: 13 });

		expect(locateAnchor('Un texte entièrement différent.', anchor)).toBeNull();
	});

	it('reports an anchor with an empty quote as not found', () => {
		const anchor = { quote: '', prefix: '', suffix: '', start_offset: 0, end_offset: 0 };

		expect(locateAnchor(TEXT, anchor)).toBeNull();
	});
});
