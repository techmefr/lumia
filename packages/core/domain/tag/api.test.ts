import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createTagApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, tags: createTagApi(recorder.http) };
}

describe('the reader tags', () => {
	it('lists them with their article count', async () => {
		const { tags, last } = api([[{ id: 't1', name: 'Cuisine', article_count: 3 }]]);
		await expect(tags.listTags()).resolves.toEqual([
			{ id: 't1', name: 'Cuisine', article_count: 3 }
		]);
		expect(last()).toMatchObject({ path: '/tags', method: 'GET' });
	});

	it('creates one from a name', async () => {
		const { tags, last } = api([{ id: 't1' }]);
		await tags.createTag('Cuisine');
		expect(last()).toMatchObject({ path: '/tags', method: 'POST', body: { name: 'Cuisine' } });
	});

	it('renames one', async () => {
		const { tags, last } = api([{ id: 't1' }]);
		await tags.renameTag('t1', 'Recettes');
		expect(last()).toMatchObject({
			path: '/tags/t1',
			method: 'PATCH',
			body: { name: 'Recettes' }
		});
	});

	it('deletes one', async () => {
		const { tags, last } = api([undefined]);
		await tags.deleteTag('t1');
		expect(last()).toMatchObject({ path: '/tags/t1', method: 'DELETE' });
	});
});

describe('on an article', () => {
	it('tags it by name', async () => {
		const { tags, last } = api([[{ id: 't1', name: 'Cuisine' }]]);
		await expect(tags.tagArticle('a1', 'Cuisine')).resolves.toEqual([
			{ id: 't1', name: 'Cuisine' }
		]);
		expect(last()).toMatchObject({
			path: '/articles/a1/tags',
			method: 'POST',
			body: { name: 'Cuisine' }
		});
	});

	it('removes one tag', async () => {
		const { tags, last } = api([[]]);
		await tags.untagArticle('a1', 't1');
		expect(last()).toMatchObject({ path: '/articles/a1/tags/t1', method: 'DELETE' });
	});

	it('reads the local suggestions with a GET', async () => {
		const { tags, last } = api([[{ name: 'recette', source: 'keyword' }]]);
		await expect(tags.getSuggestions('a1')).resolves.toEqual([
			{ name: 'recette', source: 'keyword' }
		]);
		expect(last()).toMatchObject({ path: '/articles/a1/tag-suggestions', method: 'GET' });
	});

	it('asks the model for suggestions with a POST, since that costs tokens', async () => {
		const { tags, last } = api([[]]);
		await tags.getAiSuggestions('a1');
		expect(last()).toMatchObject({ path: '/articles/a1/tag-suggestions/ai', method: 'POST' });
	});
});
