import { describe, expect, it } from 'vitest';
import { BLOCK_SEPARATOR, readableText } from './readable-text';
import { splitIntoChunks } from './speech.svelte';

function body(html: string): HTMLElement {
	const parsed = new DOMParser().parseFromString(html, 'text/html');
	return parsed.body;
}

function joined(blocks: string[]): string {
	return blocks.join(BLOCK_SEPARATOR);
}

describe('readableText', () => {
	// `textContent` welds the last sentence of a paragraph onto the first of the next, which is
	// what the voice reads out without a breath.
	it('does not weld two paragraphs together', () => {
		const root = body('<p>Une première phrase.</p><p>Une seconde phrase.</p>');

		expect(root.textContent).toBe('Une première phrase.Une seconde phrase.');
		expect(readableText(root)).toBe(joined(['Une première phrase.', 'Une seconde phrase.']));
	});

	// A heading carries no full stop, so the chunker had no sentence end to break on and swallowed
	// the paragraph after it into the same spoken chunk.
	it('closes a block that carries no punctuation of its own', () => {
		const root = body('<h2>Un intertitre</h2><p>Le paragraphe qui suit.</p>');

		expect(readableText(root)).toBe(joined(['Un intertitre.', 'Le paragraphe qui suit.']));
	});

	it('leaves a block that already ends on punctuation alone', () => {
		const root = body('<p>Une question ?</p><p>Une exclamation !</p><p>Des points…</p>');

		expect(readableText(root)).toBe(joined(['Une question ?', 'Une exclamation !', 'Des points…']));
	});

	it('gives every list item its own stop', () => {
		const root = body('<ul><li>Premier</li><li>Deuxième</li></ul>');

		expect(readableText(root)).toBe(joined(['Premier.', 'Deuxième.']));
	});

	// A blockquote holding paragraphs is a block containing blocks: counting both would read its
	// text twice.
	it('reads a nested block once', () => {
		const root = body('<blockquote><p>Une citation.</p></blockquote>');

		expect(readableText(root)).toBe('Une citation.');
	});

	it('keeps the inline markup inside a paragraph as one sentence', () => {
		const root = body('<p>Un mot <strong>en gras</strong> au milieu.</p>');

		expect(readableText(root)).toBe('Un mot en gras au milieu.');
	});

	it('collapses the whitespace the html left behind', () => {
		const root = body('<p>Deux\n\n   mots.</p>');

		expect(readableText(root)).toBe('Deux mots.');
	});

	it('skips a block with nothing to say', () => {
		const root = body('<p>Un texte.</p><p>   </p><p>Un autre.</p>');

		expect(readableText(root)).toBe(joined(['Un texte.', 'Un autre.']));
	});

	// A summary arrives as bare text rather than markup, and still has to be read.
	it('reads content that carries no block markup at all', () => {
		const root = body('Un résumé sans balise.');

		expect(readableText(root)).toBe('Un résumé sans balise.');
	});

	it('returns nothing for an empty body', () => {
		expect(readableText(body(''))).toBe('');
	});

	// The point of the separation: the chunker breaks on sentence ends, so a paragraph boundary
	// has to be one.
	it('lets the chunker break between two paragraphs', () => {
		const long = 'a'.repeat(150);
		const root = body(`<h2>${long}</h2><p>${long}</p>`);

		expect(splitIntoChunks(readableText(root))).toHaveLength(2);
		expect(splitIntoChunks(root.textContent ?? '')).toHaveLength(1);
	});
});
