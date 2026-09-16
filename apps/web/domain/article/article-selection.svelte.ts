/**
 * The set of articles a bulk action will apply to.
 *
 * It holds ids rather than indices so that appending a page cannot shift what is selected, and it
 * is emptied by the page on every reload of the list: a selection that silently survived a change
 * of feed, filter or search would let a reader modify articles they never saw. Appending with
 * "load more" keeps it, because those articles stay on screen and stay counted.
 */
export class ArticleSelection {
	isActive = $state(false);
	ids = $state<string[]>([]);
	/** Where a shift-click measures its range from: the last card touched on its own. */
	private anchorIndex = -1;

	get count(): number {
		return this.ids.length;
	}

	has(id: string): boolean {
		return this.ids.includes(id);
	}

	open(): void {
		this.isActive = true;
	}

	/** Leaves selection mode. The selection goes with it, so nothing invisible stays armed. */
	close(): void {
		this.isActive = false;
		this.clear();
	}

	clear(): void {
		this.ids = [];
		this.anchorIndex = -1;
	}

	/**
	 * Toggles one article, or takes everything between the anchor and it when `extend` is set.
	 * A range always adds: shift-clicking across a span the reader means to keep should not empty
	 * half of it because the far end happened to be selected already.
	 */
	toggle(index: number, listIds: string[], { extend = false } = {}): void {
		const id = listIds[index];
		if (id === undefined) return;
		this.isActive = true;

		if (extend && this.anchorIndex !== -1) {
			const from = Math.min(this.anchorIndex, index);
			const to = Math.max(this.anchorIndex, index);
			const span = listIds.slice(from, to + 1);
			this.ids = [...this.ids, ...span.filter((candidate) => !this.ids.includes(candidate))];
			return;
		}

		this.ids = this.has(id) ? this.ids.filter((current) => current !== id) : [...this.ids, id];
		this.anchorIndex = index;
	}

	/** Everything currently loaded — never the articles beyond the last page fetched. */
	selectAll(listIds: string[]): void {
		this.isActive = true;
		this.ids = [...listIds];
		this.anchorIndex = listIds.length - 1;
	}

	/** Drops the ids no longer in the list, so a removed article cannot stay selected unseen. */
	keepOnly(listIds: string[]): void {
		this.ids = this.ids.filter((id) => listIds.includes(id));
	}
}
