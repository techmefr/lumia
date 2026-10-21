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
		['tagId', 'tag-1', 'tag_id=tag-1'],
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

describe('getRelatedArticles', () => {
	it('asks for the related articles of one article', async () => {
		const { articles, last } = api([[]]);
		await articles.getRelatedArticles('article-1');
		expect(last()).toMatchObject({ path: '/articles/article-1/related', method: 'GET' });
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

describe('importReadingList', () => {
	it('uploads the file and its source as multipart under the names the backend reads', async () => {
		const { articles, last } = api([{ import_id: 'abc', total: 2 }]);
		const file = new File(['<ul />'], 'ril_export.html', { type: 'text/html' });
		await expect(articles.importReadingList('pocket', file)).resolves.toEqual({
			import_id: 'abc',
			total: 2
		});
		expect(last()).toMatchObject({ path: '/articles/import-reading-list', method: 'POST' });
		expect(last().formData?.get('file')).toBe(file);
		expect(last().formData?.get('source')).toBe('pocket');
		expect(last().body).toBeUndefined();
	});

	it('reads the progress of one import', async () => {
		const progress = { total: 2, saved: 1, failed: 0, finished: false };
		const { articles, last } = api([progress]);
		await expect(articles.getReadingListImportProgress('abc')).resolves.toEqual(progress);
		expect(last()).toMatchObject({ path: '/articles/import-reading-list/abc', method: 'GET' });
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

describe('getArticleAudio', () => {
	it('asks for the audio of that article, with the session', async () => {
		const { articles, last } = api([new Blob(['mp3'])]);
		await articles.getArticleAudio('article-1');
		expect(last()).toMatchObject({
			path: '/articles/article-1/audio',
			method: 'GET',
			auth: true
		});
	});

	it('hands back the file the server built', async () => {
		const audio = new Blob(['mp3'], { type: 'audio/mpeg' });
		const { articles } = api([audio]);
		expect(await articles.getArticleAudio('article-1')).toBe(audio);
	});
});

describe('exportArticleEpub', () => {
	it('asks for the epub of that article, with the session', async () => {
		const { articles, last } = api([new Blob(['epub'])]);
		await articles.exportArticleEpub('article-1');
		expect(last()).toMatchObject({
			path: '/articles/article-1/export.epub',
			method: 'GET',
			auth: true
		});
	});

	it('hands back the file the server built', async () => {
		const book = new Blob(['epub'], { type: 'application/epub+zip' });
		const { articles } = api([book]);
		expect(await articles.exportArticleEpub('article-1')).toBe(book);
	});
});

describe('public sharing', () => {
	it('reads whether the article has a link, with the session', async () => {
		const { articles, last } = api([{ enabled: true, shared: false, created_at: null }]);
		await articles.getShareStatus('article-1');
		expect(last()).toMatchObject({
			path: '/articles/article-1/share',
			method: 'GET',
			auth: true
		});
	});

	it('asks for a new link with a POST and returns the token it was given', async () => {
		const { articles, last } = api([{ token: 'secret', created_at: '2026-10-21T10:00:00Z' }]);
		const created = await articles.createShare('article-1');
		expect(last()).toMatchObject({ path: '/articles/article-1/share', method: 'POST', auth: true });
		expect(created.token).toBe('secret');
	});

	it('revokes the link with a DELETE', async () => {
		const { articles, last } = api([undefined]);
		await articles.revokeShare('article-1');
		expect(last()).toMatchObject({
			path: '/articles/article-1/share',
			method: 'DELETE',
			auth: true
		});
	});

	it('opens a public article without any session', async () => {
		const { articles, last } = api([{ title: 'Un article' }]);
		await expect(articles.getPublicArticle('tok_en')).resolves.toEqual({ title: 'Un article' });
		expect(last()).toMatchObject({ path: '/public/articles/tok_en', method: 'GET', auth: false });
	});

	it('keeps a hostile token inside its path segment', async () => {
		const { articles, last } = api([{}]);
		await articles.getPublicArticle('a/../b?x=1');
		expect(last().path).toBe('/public/articles/a%2F..%2Fb%3Fx%3D1');
	});
});
