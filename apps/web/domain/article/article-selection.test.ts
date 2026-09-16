import { describe, expect, it } from 'vitest';
import { ArticleSelection } from './article-selection.svelte';

const LIST = ['a', 'b', 'c', 'd', 'e'];

function selection(): ArticleSelection {
	return new ArticleSelection();
}

describe('picking articles one by one', () => {
	it('starts empty and out of selection mode, so the list stays free of chrome', () => {
		const state = selection();
		expect(state.isActive).toBe(false);
		expect(state.count).toBe(0);
	});

	it('takes an article and drops it again on a second click', () => {
		const state = selection();
		state.toggle(1, LIST);
		expect(state.ids).toEqual(['b']);

		state.toggle(1, LIST);
		expect(state.ids).toEqual([]);
	});

	// Clicking a checkbox is itself a way in: asking the reader to arm the mode first would make
	// the first click do nothing visible.
	it('enters selection mode as soon as something is picked', () => {
		const state = selection();
		state.toggle(0, LIST);
		expect(state.isActive).toBe(true);
	});

	it('ignores an index that is not in the list', () => {
		const state = selection();
		state.toggle(99, LIST);
		expect(state.ids).toEqual([]);
	});
});

describe('taking a range', () => {
	it('takes everything between the last article picked and this one', () => {
		const state = selection();
		state.toggle(1, LIST);
		state.toggle(3, LIST, { extend: true });
		expect(state.ids).toEqual(['b', 'c', 'd']);
	});

	it('works backwards from the anchor too', () => {
		const state = selection();
		state.toggle(3, LIST);
		state.toggle(1, LIST, { extend: true });
		expect(state.ids).toEqual(['d', 'b', 'c']);
	});

	// Shift-clicking across a span the reader means to keep must not empty half of it because the
	// far end happened to be selected already.
	it('only ever adds, never inverts what the range covers', () => {
		const state = selection();
		state.toggle(1, LIST);
		state.toggle(2, LIST);
		state.toggle(0, LIST, { extend: true });
		expect(state.ids.sort()).toEqual(['a', 'b', 'c']);
	});

	it('falls back to a plain toggle when nothing anchors the range yet', () => {
		const state = selection();
		state.toggle(2, LIST, { extend: true });
		expect(state.ids).toEqual(['c']);
	});
});

describe('selecting everything', () => {
	it('takes the loaded articles and nothing beyond them', () => {
		const state = selection();
		state.selectAll(LIST);
		expect(state.ids).toEqual(LIST);
	});

	it('opens the bar, since a selection with nothing to act on is a dead end', () => {
		const state = selection();
		state.selectAll(LIST);
		expect(state.isActive).toBe(true);
	});
});

describe('clearing', () => {
	// A selection carried across a change of feed or filter would arm a bulk action on articles
	// the reader can no longer see.
	it('empties the selection and forgets the anchor', () => {
		const state = selection();
		state.toggle(0, LIST);
		state.clear();
		state.toggle(2, LIST, { extend: true });
		expect(state.ids).toEqual(['c']);
	});

	it('leaves selection mode and empties it when the bar is closed', () => {
		const state = selection();
		state.toggle(0, LIST);
		state.close();
		expect(state.isActive).toBe(false);
		expect(state.count).toBe(0);
	});

	it('drops the ids that are no longer in the list', () => {
		const state = selection();
		state.selectAll(LIST);
		state.keepOnly(['a', 'c']);
		expect(state.ids).toEqual(['a', 'c']);
	});
});
