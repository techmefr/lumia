import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearKaraoke, highlightChunk, supportsKaraoke } from './karaoke';

/**
 * jsdom implements neither `CSS.highlights` nor `Highlight`, and the whole module is built on
 * them. This stands in for that browser api — the outer boundary — and keeps the ranges that were
 * painted, which is the module's only observable output.
 */
function rect(top: number, height = 20): DOMRect {
	return {
		top,
		bottom: top + height,
		height,
		width: height === 0 ? 0 : 200,
		left: 0,
		right: height === 0 ? 0 : 200,
		x: 0,
		y: top,
		toJSON: () => ({})
	} as DOMRect;
}

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

	// jsdom's Range has no geometry method at all, and the module measures the painted range to
	// decide whether to scroll. The default sits comfortably mid-viewport, which is the case where
	// nothing should move; a test that cares states its own.
	Object.defineProperty(Range.prototype, 'getBoundingClientRect', {
		configurable: true,
		writable: true,
		value: () => rect(window.innerHeight / 2)
	});

	return {
		painted: () => registry.get('lumia-tts')?.ranges[0] ?? null,
		names: () => [...registry.keys()]
	};
}

function article(html: string): HTMLElement {
	const root = document.createElement('div');
	root.innerHTML = html;
	document.body.appendChild(root);
	return root;
}

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
	Reflect.deleteProperty(Range.prototype, 'getBoundingClientRect');
	document.body.innerHTML = '';
});

describe('when the browser has no highlight api', () => {
	// Safari and Firefox shipped this late, so the common case has to be a reading with no
	// highlight rather than a reading that throws. The audio is what matters.
	it('reports itself unsupported', () => {
		expect(supportsKaraoke()).toBe(false);
	});

	it('paints nothing and says so', () => {
		expect(highlightChunk(article('<p>Un kiosque numérique.</p>'), 'Un kiosque')).toBe(false);
	});

	it('clears without throwing', () => {
		expect(() => clearKaraoke()).not.toThrow();
	});
});

describe('painting the spoken chunk', () => {
	let api: ReturnType<typeof fakeHighlightApi>;

	beforeEach(() => {
		api = fakeHighlightApi();
	});

	it('reports itself supported', () => {
		expect(supportsKaraoke()).toBe(true);
	});

	it('paints the chunk it was given', () => {
		const root = article('<p>Un kiosque numérique réinvente la une.</p>');

		expect(highlightChunk(root, 'kiosque numérique')).toBe(true);
		expect(api.painted()?.toString()).toBe('kiosque numérique');
	});

	it('paints under a single name, so a new chunk replaces the last', () => {
		const root = article('<p>Une phrase. Puis une autre.</p>');

		highlightChunk(root, 'Une phrase.');
		highlightChunk(root, 'Puis une autre.');

		expect(api.names()).toEqual(['lumia-tts']);
		expect(api.painted()?.toString()).toBe('Puis une autre.');
	});

	// The body is sanitised html the app injects as-is, so a sentence routinely runs across an
	// emphasis or a link. Walking the text nodes rather than the markup is what lets it match.
	it('paints across the inline markup a feed left in the sentence', () => {
		const root = article('<p>Un <em>kiosque</em> <strong>numérique</strong> réinvente.</p>');

		expect(highlightChunk(root, 'kiosque numérique')).toBe(true);
		expect(api.painted()?.toString()).toContain('kiosque');
	});

	// The spoken chunk has its whitespace collapsed; the html still carries the newlines and
	// indentation of the source. Both sides have to be collapsed the same way or nothing matches.
	it('matches text the html broke across lines', () => {
		const root = article('<p>Un kiosque\n\n    numérique réinvente.</p>');

		expect(highlightChunk(root, 'Un kiosque numérique')).toBe(true);
	});

	it('matches a chunk whose own whitespace is untidy', () => {
		const root = article('<p>Un kiosque numérique réinvente.</p>');

		expect(highlightChunk(root, '  Un   kiosque\nnumérique  ')).toBe(true);
	});

	it('paints a match at the very end of the article', () => {
		const root = article('<p>Un kiosque numérique réinvente la une.</p>');

		expect(highlightChunk(root, 'la une.')).toBe(true);
		expect(api.painted()?.toString()).toBe('la une.');
	});

	it('paints a match at the very start', () => {
		const root = article('<p>Un kiosque numérique.</p>');

		expect(highlightChunk(root, 'Un kiosque')).toBe(true);
		expect(api.painted()?.toString()).toBe('Un kiosque');
	});
});

describe('when the chunk is not in the article', () => {
	let api: ReturnType<typeof fakeHighlightApi>;

	beforeEach(() => {
		api = fakeHighlightApi();
	});

	// The reading starts with the title, which is not part of the body: the first chunk of every
	// article legitimately fails to match, and must clear rather than leave the previous highlight
	// stranded on screen.
	it('clears the previous highlight and says so', () => {
		const root = article('<p>Un kiosque numérique.</p>');
		highlightChunk(root, 'kiosque');

		expect(highlightChunk(root, 'Le titre de l’article')).toBe(false);
		expect(api.painted()).toBeNull();
	});

	it.each(['', ' ', 'a'])('refuses a chunk of %p as too short to place', (chunk) => {
		const root = article('<p>a a a a a</p>');

		expect(highlightChunk(root, chunk)).toBe(false);
		expect(api.painted()).toBeNull();
	});

	it('handles an empty article', () => {
		expect(highlightChunk(article(''), 'kiosque')).toBe(false);
	});
});

describe('clearing', () => {
	it('removes the highlight', () => {
		const api = fakeHighlightApi();
		const root = article('<p>Un kiosque numérique.</p>');
		highlightChunk(root, 'kiosque');

		clearKaraoke();

		expect(api.painted()).toBeNull();
	});

	it('is safe to call when nothing is painted', () => {
		fakeHighlightApi();
		expect(() => clearKaraoke()).not.toThrow();
	});
});

describe('following the reading down the page', () => {
	let api: ReturnType<typeof fakeHighlightApi>;

	beforeEach(() => {
		api = fakeHighlightApi();
	});

	/** jsdom lays nothing out, so the geometry of the painted range has to be stated. */
	function rangeAt(top: number, height = 20) {
		vi.spyOn(Range.prototype, 'getBoundingClientRect').mockReturnValue(rect(top, height));
	}

	it('scrolls the sentence into view when it has drifted off screen', () => {
		const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
		rangeAt(window.innerHeight * 2);

		highlightChunk(article('<p>Un kiosque numérique.</p>'), 'kiosque');

		expect(scroll).toHaveBeenCalledTimes(1);
	});

	// Scrolling on every chunk would fight the reader who has just scrolled themselves: the page
	// only moves when the sentence has actually left the comfortable middle band.
	it('leaves the page alone while the sentence is comfortably in view', () => {
		const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
		rangeAt(window.innerHeight / 2);

		highlightChunk(article('<p>Un kiosque numérique.</p>'), 'kiosque');

		expect(scroll).not.toHaveBeenCalled();
	});

	it('scrolls when the sentence is above the top of the window', () => {
		const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
		rangeAt(-200);

		highlightChunk(article('<p>Un kiosque numérique.</p>'), 'kiosque');

		expect(scroll).toHaveBeenCalledTimes(1);
	});

	// A collapsed rect means the range is not laid out — inside a hidden element, or before the
	// first paint. Scrolling to it would jump the page to the top for no reason.
	it('does not scroll to a range with no geometry', () => {
		const scroll = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
		rangeAt(0, 0);

		expect(highlightChunk(article('<p>Un kiosque numérique.</p>'), 'kiosque')).toBe(true);
		expect(scroll).not.toHaveBeenCalled();
		expect(api.painted()).not.toBeNull();
	});
});
