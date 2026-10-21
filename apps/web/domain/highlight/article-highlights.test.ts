import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Highlight, HighlightApi } from '@lumia/core';
import { ArticleHighlights } from './article-highlights.svelte';

function stored(id: string, quote: string, start: number, note: string | null = null): Highlight {
	return {
		id,
		article_id: 'article-1',
		article_title: 'Titre',
		quote,
		prefix: '',
		suffix: '',
		start_offset: start,
		end_offset: start + quote.length,
		note,
		created_at: '2026-10-21T08:00:00Z'
	};
}

function fakeApi(initial: Highlight[] = []) {
	let rows = [...initial];
	const api = {
		listArticleHighlights: vi.fn(async () => [...rows]),
		createHighlight: vi.fn(async (_articleId: string, draft: Omit<Highlight, 'id'>) => {
			const created = { ...stored(`new-${rows.length}`, draft.quote, draft.start_offset), ...draft };
			rows = [...rows, created as Highlight];
			return created as Highlight;
		}),
		updateHighlightNote: vi.fn(async (id: string, note: string | null) => {
			const row = rows.find((candidate) => candidate.id === id)!;
			return { ...row, note };
		}),
		deleteHighlight: vi.fn(async (id: string) => {
			rows = rows.filter((candidate) => candidate.id !== id);
		})
	} satisfies Pick<
		HighlightApi,
		'listArticleHighlights' | 'createHighlight' | 'updateHighlightNote' | 'deleteHighlight'
	>;
	return api;
}

let root: HTMLElement;

function select(from: number, to: number): Range {
	const text = root.querySelector('p')!.firstChild!;
	const range = document.createRange();
	range.setStart(text, from);
	range.setEnd(text, to);
	return range;
}

beforeEach(() => {
	root = document.createElement('div');
	root.innerHTML = '<p>Sur le papier et l encre.</p>';
	document.body.appendChild(root);
});

afterEach(() => {
	document.body.innerHTML = '';
});

describe('loading', () => {
	it('keeps what the api returns and finds each passage in the text', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('a', 'papier', 7)]));
		highlights.attach(root);

		await highlights.load('article-1');

		expect(highlights.items.map((item) => item.id)).toEqual(['a']);
		expect(highlights.isOrphan('a')).toBe(false);
		expect(highlights.canReveal('a')).toBe(true);
	});

	it('flags a passage that is gone from the text as an orphan, and still keeps it', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('gone', 'texte disparu', 0)]));
		highlights.attach(root);

		await highlights.load('article-1');

		expect(highlights.isOrphan('gone')).toBe(true);
		expect(highlights.canReveal('gone')).toBe(false);
		expect(highlights.items).toHaveLength(1);
	});

	it('has no orphans while the text is not attached, since nothing can be located', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('a', 'papier', 7)]));

		await highlights.load('article-1');

		expect(highlights.orphanIds).toEqual([]);
		expect(highlights.canReveal('a')).toBe(false);
	});

	it('locates again when the text is attached after the highlights arrived', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('gone', 'texte disparu', 0)]));
		await highlights.load('article-1');

		highlights.attach(root);

		expect(highlights.orphanIds).toEqual(['gone']);
	});
});

describe('selecting and committing', () => {
	it('turns a selection into a pending anchor', () => {
		const highlights = new ArticleHighlights(fakeApi());
		highlights.attach(root);

		highlights.capture(select(7, 13));

		expect(highlights.pending).toMatchObject({ quote: 'papier', start_offset: 7 });
	});

	it('drops the pending anchor when the selection goes away', () => {
		const highlights = new ArticleHighlights(fakeApi());
		highlights.attach(root);
		highlights.capture(select(7, 13));

		highlights.capture(null);

		expect(highlights.pending).toBeNull();
	});

	it('captures nothing while the text is not attached', () => {
		const highlights = new ArticleHighlights(fakeApi());

		highlights.capture(select(7, 13));

		expect(highlights.pending).toBeNull();
	});

	it('saves the pending passage, lists it in reading order and clears the selection', async () => {
		const api = fakeApi([stored('late', 'encre', 22)]);
		const highlights = new ArticleHighlights(api);
		highlights.attach(root);
		await highlights.load('article-1');
		highlights.capture(select(7, 13));

		const created = await highlights.commit('article-1');

		expect(created?.quote).toBe('papier');
		expect(api.createHighlight).toHaveBeenCalledWith(
			'article-1',
			expect.objectContaining({ quote: 'papier', start_offset: 7, end_offset: 13 })
		);
		expect(highlights.items.map((item) => item.quote)).toEqual(['papier', 'encre']);
		expect(highlights.pending).toBeNull();
	});

	it('does nothing when there is no selection to save', async () => {
		const api = fakeApi();
		const highlights = new ArticleHighlights(api);
		highlights.attach(root);

		await expect(highlights.commit('article-1')).resolves.toBeNull();
		expect(api.createHighlight).not.toHaveBeenCalled();
	});

	it('keeps the selection when saving fails, so the reader can try again', async () => {
		const api = fakeApi();
		api.createHighlight.mockRejectedValueOnce(new Error('offline'));
		const highlights = new ArticleHighlights(api);
		highlights.attach(root);
		highlights.capture(select(7, 13));

		await expect(highlights.commit('article-1')).rejects.toThrow('offline');

		expect(highlights.pending).not.toBeNull();
		expect(highlights.items).toEqual([]);
	});
});

describe('editing and removing', () => {
	it('replaces the highlight with the saved note', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('a', 'papier', 7)]));
		await highlights.load('article-1');

		await highlights.saveNote('a', 'A thought');

		expect(highlights.items[0].note).toBe('A thought');
	});

	it('removes a highlight from the list and from the text', async () => {
		const api = fakeApi([stored('a', 'papier', 7)]);
		const highlights = new ArticleHighlights(api);
		highlights.attach(root);
		await highlights.load('article-1');

		await highlights.remove('a');

		expect(api.deleteHighlight).toHaveBeenCalledWith('a');
		expect(highlights.items).toEqual([]);
		expect(highlights.canReveal('a')).toBe(false);
	});

	it('scrolls to a passage that is in the text', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('a', 'papier', 7)]));
		highlights.attach(root);
		await highlights.load('article-1');
		const scrollIntoView = vi.fn();
		root.querySelector('p')!.scrollIntoView = scrollIntoView;

		highlights.reveal('a');

		expect(scrollIntoView).toHaveBeenCalledOnce();
	});

	it('has nothing to scroll to for a passage that is not in the text', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('gone', 'texte disparu', 0)]));
		highlights.attach(root);
		await highlights.load('article-1');
		const scrollIntoView = vi.fn();
		root.querySelector('p')!.scrollIntoView = scrollIntoView;

		highlights.reveal('gone');

		expect(scrollIntoView).not.toHaveBeenCalled();
	});

	it('lets go of the text on dispose', async () => {
		const highlights = new ArticleHighlights(fakeApi([stored('a', 'papier', 7)]));
		highlights.attach(root);
		await highlights.load('article-1');

		highlights.dispose();

		expect(highlights.canReveal('a')).toBe(false);
	});
});
