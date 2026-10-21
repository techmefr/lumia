import type { HighlightAnchor } from './types';

/** Characters of surrounding text kept on each side; the API accepts up to 200. */
export const ANCHOR_CONTEXT_LENGTH = 32;

export interface TextRange {
	start: number;
	end: number;
}

/** Cuts the anchor of the passage `[start, end)` out of the article's flattened text. */
export function buildAnchor(text: string, { start, end }: TextRange): HighlightAnchor {
	return {
		quote: text.slice(start, end),
		prefix: text.slice(Math.max(0, start - ANCHOR_CONTEXT_LENGTH), start),
		suffix: text.slice(end, end + ANCHOR_CONTEXT_LENGTH),
		start_offset: start,
		end_offset: end
	};
}

/**
 * Finds a stored passage in the article's current flattened text, or null when it is gone.
 *
 * The stored offset is only trusted when it still lands on the quote. Otherwise every occurrence
 * of the quote competes: the one whose surroundings match the stored context best wins, then the
 * one closest to the old offset. A passage that is not found is reported, never guessed at.
 */
export function locateAnchor(text: string, anchor: HighlightAnchor): TextRange | null {
	const { quote, start_offset: hint } = anchor;
	if (quote.length === 0) return null;
	if (text.slice(hint, hint + quote.length) === quote) {
		return { start: hint, end: hint + quote.length };
	}

	let best: { start: number; score: number; distance: number } | null = null;
	let from = text.indexOf(quote);
	while (from !== -1) {
		const score = contextScore(text, from, quote.length, anchor);
		const distance = Math.abs(from - hint);
		if (best === null || score > best.score || (score === best.score && distance < best.distance)) {
			best = { start: from, score, distance };
		}
		from = text.indexOf(quote, from + 1);
	}
	return best === null ? null : { start: best.start, end: best.start + quote.length };
}

function contextScore(text: string, start: number, length: number, anchor: HighlightAnchor): number {
	const before = text.slice(Math.max(0, start - anchor.prefix.length), start);
	const after = text.slice(start + length, start + length + anchor.suffix.length);
	return commonSuffixLength(before, anchor.prefix) + commonPrefixLength(after, anchor.suffix);
}

function commonPrefixLength(left: string, right: string): number {
	let length = 0;
	while (length < left.length && length < right.length && left[length] === right[length]) length += 1;
	return length;
}

function commonSuffixLength(left: string, right: string): number {
	let length = 0;
	while (
		length < left.length &&
		length < right.length &&
		left[left.length - 1 - length] === right[right.length - 1 - length]
	) {
		length += 1;
	}
	return length;
}
