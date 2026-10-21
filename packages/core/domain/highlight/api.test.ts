import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createHighlightApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, highlights: createHighlightApi(recorder.http) };
}

describe('the highlight api', () => {
	it('lists every highlight of the reader', async () => {
		const { highlights, last } = api([[{ id: 'highlight-1' }]]);
		await expect(highlights.listHighlights()).resolves.toEqual([{ id: 'highlight-1' }]);
		expect(last()).toMatchObject({ path: '/highlights', method: 'GET' });
	});

	it('lists the highlights of one article', async () => {
		const { highlights, last } = api();
		await highlights.listArticleHighlights('article-1');
		expect(last()).toMatchObject({ path: '/articles/article-1/highlights', method: 'GET' });
	});

	it('creates a highlight with its anchor and note', async () => {
		const { highlights, last } = api([{ id: 'highlight-2' }]);
		const draft = {
			quote: 'le papier',
			prefix: 'Sur ',
			suffix: ' et',
			start_offset: 4,
			end_offset: 13,
			note: 'A thought'
		};
		await highlights.createHighlight('article-1', draft);
		expect(last()).toMatchObject({
			path: '/articles/article-1/highlights',
			method: 'POST',
			body: draft
		});
	});

	it('edits the note of a highlight', async () => {
		const { highlights, last } = api([{ id: 'highlight-1' }]);
		await highlights.updateHighlightNote('highlight-1', 'New note');
		expect(last()).toMatchObject({
			path: '/highlights/highlight-1',
			method: 'PATCH',
			body: { note: 'New note' }
		});
	});

	it('clears a note by sending null', async () => {
		const { highlights, last } = api([{ id: 'highlight-1' }]);
		await highlights.updateHighlightNote('highlight-1', null);
		expect(last().body).toEqual({ note: null });
	});

	it('deletes a highlight', async () => {
		const { highlights, last } = api([undefined]);
		await highlights.deleteHighlight('highlight-1');
		expect(last()).toMatchObject({ path: '/highlights/highlight-1', method: 'DELETE' });
	});
});
