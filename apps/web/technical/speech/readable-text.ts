/**
 * Turns an article body into the text a voice should read.
 *
 * `textContent` is the obvious answer and the wrong one: it concatenates nodes with nothing in
 * between, so the last sentence of a paragraph runs straight into the first of the next. The
 * voice never breathes, and a block that ends without punctuation — a heading, a list item — is
 * welded to what follows inside a single spoken chunk, which also makes the karaoke highlight
 * lose the chunk it is looking for.
 */

/**
 * Marks a block boundary in the text handed to the reader. A control character rather than a
 * newline: article text carries newlines of its own, and they mean nothing to the ear.
 */
export const BLOCK_SEPARATOR = '';

/** The blocks a reader hears as separate: each one earns a stop. */
const BLOCK_SELECTOR =
	'p, li, h1, h2, h3, h4, h5, h6, blockquote, pre, figcaption, td, th, dt, dd';

const ENDS_A_SENTENCE = /[.!?…:;»"')\]]$/;

export function readableText(root: ParentNode): string {
	const leafBlocks = Array.from(root.querySelectorAll(BLOCK_SELECTOR)).filter(
		// A blockquote wrapping paragraphs would otherwise contribute its text twice.
		(element) => element.querySelector(BLOCK_SELECTOR) === null
	);

	const blocks = leafBlocks.map((element) => collapse(element.textContent ?? '')).filter(Boolean);
	// Content with no block markup at all — a bare summary, typically — still has to be read.
	if (blocks.length === 0) return collapse(root.textContent ?? '');

	// The chunker treats the separator as a boundary no spoken chunk may straddle, which also
	// keeps every chunk inside a single block for the karaoke highlight.
	return blocks.map(closeSentence).join(BLOCK_SEPARATOR);
}

function closeSentence(block: string): string {
	return ENDS_A_SENTENCE.test(block) ? block : `${block}.`;
}

function collapse(value: string): string {
	return value.replace(/\s+/g, ' ').trim();
}
