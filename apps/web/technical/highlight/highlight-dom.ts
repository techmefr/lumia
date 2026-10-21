/**
 * The thin DOM side of highlights. The anchoring itself is pure and lives in `@lumia/core`; this
 * file only converts between a browser Range and offsets in the article's flattened text, and
 * paints with the Custom Highlight API, which touches neither the markup nor the layout of HTML
 * the app does not own. Without that API nothing is painted and the list still carries the notes.
 */
import {
	buildAnchor,
	locateAnchor,
	type Highlight,
	type HighlightAnchor
} from '@lumia/core';
import { flatten, supportsKaraoke, type FlatText } from '../speech/karaoke';

const HIGHLIGHT_NAME = 'lumia-highlight';

export interface LocatedHighlights {
	ranges: Map<string, Range>;
	orphanIds: string[];
}

export function supportsHighlightPaint(): boolean {
	return supportsKaraoke();
}

/** The anchor of what the reader selected inside `root`, or null when nothing usable is. */
export function anchorOfRange(root: HTMLElement, range: Range): HighlightAnchor | null {
	if (range.collapsed || !root.contains(range.commonAncestorContainer)) return null;

	const flat = flatten(root);
	let start = firstIndex(flat, (node, offset) => range.comparePoint(node, offset) >= 0);
	let end = firstIndex(flat, (node, offset) => range.comparePoint(node, offset + 1) > 0);

	while (start < end && flat.text[start] === ' ') start += 1;
	while (end > start && flat.text[end - 1] === ' ') end -= 1;
	if (end <= start) return null;

	return buildAnchor(flat.text, { start, end });
}

/** Where each highlight sits in the current content; the ones that no longer match are orphans. */
export function locateHighlights(root: HTMLElement, highlights: Highlight[]): LocatedHighlights {
	const flat = flatten(root);
	const ranges = new Map<string, Range>();
	const orphanIds: string[] = [];

	for (const highlight of highlights) {
		const found = locateAnchor(flat.text, highlight);
		if (found === null) {
			orphanIds.push(highlight.id);
			continue;
		}
		ranges.set(highlight.id, rangeOf(flat, found.start, found.end));
	}
	return { ranges, orphanIds };
}

export function paintHighlights(ranges: Iterable<Range>): void {
	if (!supportsHighlightPaint()) return;
	const all = [...ranges];
	if (all.length === 0) {
		clearHighlightPaint();
		return;
	}
	CSS.highlights.set(HIGHLIGHT_NAME, new Highlight(...all));
}

export function clearHighlightPaint(): void {
	if (!supportsHighlightPaint()) return;
	CSS.highlights.delete(HIGHLIGHT_NAME);
}

export function revealRange(range: Range): void {
	range.startContainer.parentElement?.scrollIntoView?.({ block: 'center', behavior: 'smooth' });
}

function rangeOf(flat: FlatText, start: number, end: number): Range {
	const range = document.createRange();
	range.setStart(flat.nodes[start], flat.offsets[start]);
	range.setEnd(flat.nodes[end - 1], flat.offsets[end - 1] + 1);
	return range;
}

/** Smallest index whose character satisfies `predicate`, which must flip once, in document order. */
function firstIndex(flat: FlatText, predicate: (node: Text, offset: number) => boolean): number {
	let low = 0;
	let high = flat.text.length;
	while (low < high) {
		const middle = (low + high) >> 1;
		if (predicate(flat.nodes[middle], flat.offsets[middle])) high = middle;
		else low = middle + 1;
	}
	return low;
}
