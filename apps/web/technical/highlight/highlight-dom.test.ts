import { afterEach, describe, expect, it, vi } from 'vitest';
import type { Highlight } from '@lumia/core';
import {
	anchorOfRange,
	clearHighlightPaint,
	locateHighlights,
	paintHighlights,
	revealRange,
	supportsHighlightPaint
} from './highlight-dom';

/**
 * jsdom implements neither `CSS.highlights` nor `Highlight`, so painting is checked against a stand
 * in for that browser api, the outer boundary, whose registry is the observable output.
 */
function fakeHighlightApi() {
	const registry = new Map<string, { ranges: Range[] }>();
	class FakeHighlight {
		ranges: Range[];
		constructor(...ranges: Range[]) {
			this.ranges = ranges;
		}
	}
	vi.stubGlobal('Highlight', FakeHighlight);
	vi.stubGlobal('CSS', { highlights: registry });
	return { painted: () => registry.get('lumia-highlight')?.ranges ?? null };
}

function article(html: string): HTMLElement {
	const root = document.createElement('div');
	root.innerHTML = html;
	document.body.appendChild(root);
	return root;
}

function selecting(root: HTMLElement, from: [Node, number], to: [Node, number]): Range {
	const range = document.createRange();
	range.setStart(from[0], from[1]);
	range.setEnd(to[0], to[1]);
	return range;
}

function stored(id: string, quote: string, start: number, prefix = '', suffix = ''): Highlight {
	return {
		id,
		article_id: 'article-1',
		article_title: 'Titre',
		quote,
		prefix,
		suffix,
		start_offset: start,
		end_offset: start + quote.length,
		note: null,
		created_at: '2026-10-21T08:00:00Z'
	};
}

afterEach(() => {
	vi.unstubAllGlobals();
	document.body.innerHTML = '';
});

describe('anchoring a selection', () => {
	it('reads the passage and its context from a selection inside one text node', () => {
		const root = article('<p>Sur le papier et l encre.</p>');
		const text = root.querySelector('p')!.firstChild!;

		const anchor = anchorOfRange(root, selecting(root, [text, 4], [text, 13]));

		expect(anchor).toMatchObject({
			quote: 'le papier',
			prefix: 'Sur ',
			start_offset: 4,
			end_offset: 13
		});
		expect(anchor?.suffix).toBe(' et l encre.');
	});

	it('spans several elements', () => {
		const root = article('<p>Sur <em>le papier</em> et l encre.</p>');
		const first = root.querySelector('p')!.firstChild!;
		const last = root.querySelector('p')!.lastChild!;

		const anchor = anchorOfRange(root, selecting(root, [first, 0], [last, 3]));

		expect(anchor?.quote).toBe('Sur le papier et');
	});

	it('counts offsets in the collapsed text, so paragraph whitespace does not shift them', () => {
		const root = article('<p>Un</p>\n\n   <p>deux trois</p>');
		const text = root.querySelectorAll('p')[1].firstChild!;

		const anchor = anchorOfRange(root, selecting(root, [text, 5], [text, 10]));

		expect(anchor?.quote).toBe('trois');
		expect(anchor?.start_offset).toBe(8);
	});

	it('drops the whitespace at the edges of the selection', () => {
		const root = article('<p>Sur le papier et</p>');
		const text = root.querySelector('p')!.firstChild!;

		const anchor = anchorOfRange(root, selecting(root, [text, 3], [text, 14]));

		expect(anchor?.quote).toBe('le papier');
	});

	it('ignores a collapsed selection', () => {
		const root = article('<p>Sur le papier</p>');
		const text = root.querySelector('p')!.firstChild!;

		expect(anchorOfRange(root, selecting(root, [text, 4], [text, 4]))).toBeNull();
	});

	it('ignores a selection made of whitespace only', () => {
		const root = article('<p>Sur le papier</p>');
		const text = root.querySelector('p')!.firstChild!;

		expect(anchorOfRange(root, selecting(root, [text, 3], [text, 4]))).toBeNull();
	});

	it('ignores a selection outside the article', () => {
		const root = article('<p>Dans</p>');
		const outside = article('<p>Dehors</p>').firstChild!.firstChild!;

		expect(anchorOfRange(root, selecting(root, [outside, 0], [outside, 3]))).toBeNull();
	});
});

describe('locating stored highlights', () => {
	it('turns a stored anchor back into a range over the same words', () => {
		const root = article('<p>Sur <em>le papier</em> et l encre.</p>');

		const { ranges, orphanIds } = locateHighlights(root, [stored('h1', 'le papier', 4)]);

		expect(orphanIds).toEqual([]);
		expect(ranges.get('h1')?.toString()).toBe('le papier');
	});

	it('finds a highlight again after the content was extracted anew', () => {
		const root = article('<h1>Nouveau titre</h1><p>Sur le papier et l encre.</p>');

		const { ranges } = locateHighlights(root, [stored('h1', 'le papier', 4, 'Sur ', ' et')]);

		expect(ranges.get('h1')?.toString()).toBe('le papier');
	});

	it('marks a highlight whose text is gone as an orphan and keeps the others', () => {
		const root = article('<p>Sur le papier et l encre.</p>');

		const { ranges, orphanIds } = locateHighlights(root, [
			stored('gone', 'texte disparu', 0),
			stored('kept', 'encre', 22)
		]);

		expect(orphanIds).toEqual(['gone']);
		expect([...ranges.keys()]).toEqual(['kept']);
	});
});

describe('painting', () => {
	it('registers one highlight holding every range', () => {
		const api = fakeHighlightApi();
		const root = article('<p>Sur le papier et l encre.</p>');
		const { ranges } = locateHighlights(root, [stored('a', 'papier', 7), stored('b', 'encre', 22)]);

		paintHighlights(ranges.values());

		expect(api.painted()?.map((range) => range.toString())).toEqual(['papier', 'encre']);
	});

	it('removes the paint when nothing is left to show', () => {
		const api = fakeHighlightApi();
		const root = article('<p>Sur le papier.</p>');
		paintHighlights(locateHighlights(root, [stored('a', 'papier', 7)]).ranges.values());

		paintHighlights([]);

		expect(api.painted()).toBeNull();
	});

	it('clears on request', () => {
		const api = fakeHighlightApi();
		const root = article('<p>Sur le papier.</p>');
		paintHighlights(locateHighlights(root, [stored('a', 'papier', 7)]).ranges.values());

		clearHighlightPaint();

		expect(api.painted()).toBeNull();
	});

	it('does nothing, without failing, where the browser lacks the api', () => {
		expect(supportsHighlightPaint()).toBe(false);
		const root = article('<p>Sur le papier.</p>');
		const { ranges } = locateHighlights(root, [stored('a', 'papier', 7)]);

		expect(() => paintHighlights(ranges.values())).not.toThrow();
		expect(() => clearHighlightPaint()).not.toThrow();
	});
});

describe('revealing', () => {
	it('scrolls the element holding the passage to the middle of the screen', () => {
		const root = article('<p>Sur le papier.</p>');
		const paragraph = root.querySelector('p')!;
		const scrollIntoView = vi.fn();
		paragraph.scrollIntoView = scrollIntoView;
		const { ranges } = locateHighlights(root, [stored('a', 'papier', 7)]);

		revealRange(ranges.get('a')!);

		expect(scrollIntoView).toHaveBeenCalledWith({ block: 'center', behavior: 'smooth' });
	});
});
