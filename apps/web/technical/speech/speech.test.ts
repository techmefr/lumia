import { describe, expect, it } from 'vitest';
import { splitIntoChunks } from './speech.svelte';

const MAX = 220;

describe('splitIntoChunks', () => {
	it('returns nothing for empty text', () => {
		expect(splitIntoChunks('')).toEqual([]);
	});

	it('returns nothing for whitespace alone', () => {
		expect(splitIntoChunks('   \n\t ')).toEqual([]);
	});

	it('keeps a short paragraph in one piece', () => {
		expect(splitIntoChunks('Un kiosque numérique. Et une une.')).toEqual([
			'Un kiosque numérique. Et une une.'
		]);
	});

	it('collapses the whitespace the html left behind', () => {
		expect(splitIntoChunks('Deux\n\n  mots.')).toEqual(['Deux mots.']);
	});

	it('never exceeds the chunk ceiling the engines choke on', () => {
		const text = Array.from({ length: 40 }, (_, i) => `Phrase numéro ${i} un peu longue.`).join(' ');
		expect(splitIntoChunks(text).every((chunk) => chunk.length <= MAX)).toBe(true);
	});

	it('loses no word, so nothing goes unspoken', () => {
		const text = Array.from({ length: 40 }, (_, i) => `Phrase numéro ${i} un peu longue.`).join(' ');
		const words = (value: string) => value.split(/\s+/).filter(Boolean);
		expect(words(splitIntoChunks(text).join(' '))).toEqual(words(text));
	});

	it('breaks on sentence ends rather than mid-sentence', () => {
		const text = `${'a'.repeat(150)}. ${'b'.repeat(150)}.`;
		const chunks = splitIntoChunks(text);
		expect(chunks).toHaveLength(2);
		expect(chunks.every((chunk) => chunk.endsWith('.'))).toBe(true);
	});

	it.each(['!', '?', '…'])('treats %s as a sentence end too', (mark) => {
		const text = `${'a'.repeat(150)}${mark} ${'b'.repeat(150)}.`;
		expect(splitIntoChunks(text)).toHaveLength(2);
	});

	it('still breaks a single sentence too long to speak in one go', () => {
		const text = `${Array.from({ length: 60 }, () => 'mot').join(' ')}.`;
		const chunks = splitIntoChunks(text);
		expect(chunks.length).toBeGreaterThan(1);
		expect(chunks.every((chunk) => chunk.length <= MAX)).toBe(true);
	});

	it('breaks that long sentence on whitespace, never inside a word', () => {
		const text = `${Array.from({ length: 60 }, () => 'anticonstitutionnellement').join(' ')}.`;
		const chunks = splitIntoChunks(text);
		expect(chunks.every((chunk) => !chunk.startsWith('nellement'))).toBe(true);
		expect(chunks.join(' ')).toContain('anticonstitutionnellement anticonstitutionnellement');
	});

	it('leaves no empty chunk, which would be a silent gap in the reading', () => {
		const text = `Court. ${'a'.repeat(400)}. Court aussi.`;
		expect(splitIntoChunks(text).every((chunk) => chunk.trim().length > 0)).toBe(true);
	});

	it('packs several short sentences together rather than one chunk each', () => {
		const text = 'Un. Deux. Trois. Quatre. Cinq.';
		expect(splitIntoChunks(text)).toHaveLength(1);
	});

	it('handles text with no terminal punctuation at all', () => {
		expect(splitIntoChunks('Un titre sans point')).toEqual(['Un titre sans point']);
	});
});
