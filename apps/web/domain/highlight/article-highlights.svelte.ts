import type { Highlight, HighlightAnchor, HighlightApi } from '@lumia/core';
import {
	anchorOfRange,
	clearHighlightPaint,
	locateHighlights,
	paintHighlights,
	revealRange
} from '$technical/highlight/highlight-dom';

type Api = Pick<
	HighlightApi,
	'listArticleHighlights' | 'createHighlight' | 'updateHighlightNote' | 'deleteHighlight'
>;

/**
 * The highlights of the article on screen: what is stored, what the reader has just selected, and
 * where each stored passage sits in the text as it is displayed right now.
 *
 * The positions are recomputed against the live content every time (`sync`) rather than stored
 * with the highlight, which is what lets a passage survive the article being extracted again.
 */
export class ArticleHighlights {
	items = $state<Highlight[]>([]);
	/** Stored highlights whose text is no longer in the article; kept and shown, never dropped. */
	orphanIds = $state<string[]>([]);
	/** The passage currently selected, ready to be turned into a highlight. */
	pending = $state<HighlightAnchor | null>(null);

	#api: Api;
	#root: HTMLElement | null = null;
	#ranges = new Map<string, Range>();

	constructor(api: Api) {
		this.#api = api;
	}

	async load(articleId: string): Promise<void> {
		this.items = await this.#api.listArticleHighlights(articleId);
		this.sync();
	}

	/** Points at the element holding the article text, or null while it is not shown as is. */
	attach(root: HTMLElement | null): void {
		this.#root = root;
		this.pending = null;
		this.sync();
	}

	capture(range: Range | null): void {
		this.pending = this.#root && range ? anchorOfRange(this.#root, range) : null;
	}

	async commit(articleId: string): Promise<Highlight | null> {
		const anchor = this.pending;
		if (anchor === null) return null;
		const created = await this.#api.createHighlight(articleId, anchor);
		this.items = [...this.items, created].sort((a, b) => a.start_offset - b.start_offset);
		this.pending = null;
		this.sync();
		return created;
	}

	async saveNote(highlightId: string, note: string | null): Promise<void> {
		const updated = await this.#api.updateHighlightNote(highlightId, note);
		this.items = this.items.map((item) => (item.id === highlightId ? updated : item));
	}

	async remove(highlightId: string): Promise<void> {
		await this.#api.deleteHighlight(highlightId);
		this.items = this.items.filter((item) => item.id !== highlightId);
		this.sync();
	}

	isOrphan(highlightId: string): boolean {
		return this.orphanIds.includes(highlightId);
	}

	/** True when the passage is in the text and can be scrolled to. */
	canReveal(highlightId: string): boolean {
		return this.#ranges.has(highlightId);
	}

	reveal(highlightId: string): void {
		const range = this.#ranges.get(highlightId);
		if (range) revealRange(range);
	}

	dispose(): void {
		this.#root = null;
		this.#ranges.clear();
		clearHighlightPaint();
	}

	sync(): void {
		if (this.#root === null) {
			this.#ranges.clear();
			this.orphanIds = [];
			clearHighlightPaint();
			return;
		}
		const located = locateHighlights(this.#root, this.items);
		this.#ranges = located.ranges;
		this.orphanIds = located.orphanIds;
		paintHighlights(located.ranges.values());
	}
}
