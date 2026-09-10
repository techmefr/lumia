import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createArticleApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, articles: createArticleApi(recorder.http) };
}

describe('listArticles', () => {
	it('asks for the plain collection when nothing is filtered', async () => {
		const { articles, last } = api();
		await articles.listArticles();
		expect(last()).toMatchObject({ path: '/articles', method: 'GET' });
	});

	it('returns what the backend answered', async () => {
		const { articles } = api([[{ id: 'article-1' }]]);
		await expect(articles.listArticles()).resolves.toEqual([{ id: 'article-1' }]);
	});

	// The frontend speaks camelCase and the api speaks snake_case; getting one of these wrong is a
	// silently ignored filter, which looks like a backend bug.
	it.each([
		['folderId', 'folder-1', 'folder_id=folder-1'],
		['feedId', 'feed-1', 'feed_id=feed-1'],
		['authorId', 'author-1', 'author_id=author-1'],
		['categoryId', 'cat-1', 'category_id=cat-1'],
		['keywordId', 'kw-1', 'keyword_id=kw-1'],
		['query', 'kiosque', 'q=kiosque'],
		['sort', 'relevance', 'sort=relevance'],
		['limit', 50, 'limit=50'],
		['offset', 20, 'offset=20']
	] as const)('sends %s as %s', async (key, value, expected) => {
		const { articles, last } = api();
		await articles.listArticles({ [key]: value });
		expect(last().path).toBe(`/articles?${expected}`);
	});

	it('url-encodes a search term with a space', async () => {
		const { articles, last } = api();
		await articles.listArticles({ query: 'web lent' });
		expect(last().path).toBe('/articles?q=web+lent');
	});

	it('sends unread_only only when it is actually on', async () => {
		const { articles, last } = api();
		await articles.listArticles({ unreadOnly: true });
		expect(last().path).toBe('/articles?unread_only=true');
	});

	it('omits unread_only when off, rather than sending false', async () => {
		const { articles, last } = api();
		await articles.listArticles({ unreadOnly: false });
		expect(last().path).toBe('/articles');
	});

	it('combines several filters in one query', async () => {
		const { articles, last } = api();
		await articles.listArticles({ folderId: 'folder-1', unreadOnly: true, limit: 10 });
		expect(last().path).toBe('/articles?folder_id=folder-1&unread_only=true&limit=10');
	});

	it('keeps a zero offset, which is a value and not an absence', async () => {
		const { articles, last } = api();
		await articles.listArticles({ offset: 0 });
		expect(last().path).toBe('/articles?offset=0');
	});
});

describe('getArticle', () => {
	it('asks for the article by id', async () => {
		const { articles, last } = api([{ id: 'article-1' }]);
		await articles.getArticle('article-1');
		expect(last()).toMatchObject({ path: '/articles/article-1', method: 'GET' });
	});
});

describe('saveUrl', () => {
	it('posts the url to the save endpoint', async () => {
		const { articles, last } = api([{ id: 'article-9' }]);
		await articles.saveUrl('https://blog.test/post');
		expect(last()).toMatchObject({
			path: '/articles/save-url',
			method: 'POST',
			body: { url: 'https://blog.test/post' }
		});
	});

	it('sends it authenticated: an article is saved onto someone in particular', async () => {
		const { articles, last } = api([{ id: 'article-9' }]);
		await articles.saveUrl('https://blog.test/post');
		expect(last().auth).toBe(true);
	});
});

describe('translateArticle', () => {
	it('posts the target language to the article translation endpoint', async () => {
		const { articles, last } = api([{ target_lang: 'fr', title: 'Titre', content: 'Corps' }]);
		await articles.translateArticle('article-1', 'fr');
		expect(last()).toMatchObject({
			path: '/articles/article-1/translate',
			method: 'POST',
			body: { target_lang: 'fr' }
		});
	});

	it('returns the translation the server computed', async () => {
		const translation = { target_lang: 'de', title: 'Titel', content: 'Inhalt' };
		const { articles } = api([translation]);
		expect(await articles.translateArticle('article-1', 'de')).toEqual(translation);
	});
});
