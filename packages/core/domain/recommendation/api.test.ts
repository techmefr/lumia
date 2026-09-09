import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createRecommendationApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, recommendation: createRecommendationApi(recorder.http) };
}

describe('the curated lists', () => {
	it.each([
		['getEtincelle', '/articles/etincelle'],
		['getSaved', '/articles/saved'],
		['getFavorites', '/articles/favorites']
	] as const)('%s pages from the start by default', async (method, path) => {
		const { recommendation, last } = api();
		await recommendation[method]();
		expect(last().path).toBe(`${path}?limit=20&offset=0`);
	});

	it.each([
		['getEtincelle', '/articles/etincelle'],
		['getSaved', '/articles/saved'],
		['getFavorites', '/articles/favorites']
	] as const)('%s carries an explicit page through', async (method, path) => {
		const { recommendation, last } = api();
		await recommendation[method](5, 40);
		expect(last().path).toBe(`${path}?limit=5&offset=40`);
	});

	it('returns the articles the backend answered', async () => {
		const { recommendation } = api([[{ id: 'article-1' }]]);
		await expect(recommendation.getEtincelle()).resolves.toEqual([{ id: 'article-1' }]);
	});
});

describe('sendFeedback', () => {
	it('posts the update under the article it is about', async () => {
		const { recommendation, last } = api([undefined]);
		await recommendation.sendFeedback('article-7', { favorite: true });
		expect(last()).toMatchObject({
			path: '/articles/article-7/feedback',
			method: 'POST',
			body: { favorite: true }
		});
	});
});

describe('markRead', () => {
	it('sends the scope as given, so the backend decides what it covers', async () => {
		const { recommendation, last } = api([{ updated: 12 }]);
		await expect(recommendation.markRead({ folder_id: 'folder-1' })).resolves.toEqual({
			updated: 12
		});
		expect(last()).toMatchObject({
			path: '/articles/mark-read',
			method: 'POST',
			body: { folder_id: 'folder-1' }
		});
	});

	it('accepts an empty scope, which marks everything', async () => {
		const { recommendation, last } = api([{ updated: 340 }]);
		await recommendation.markRead({});
		expect(last().body).toEqual({});
	});
});

describe('the filter rules', () => {
	it('lists them', async () => {
		const { recommendation, last } = api([[]]);
		await recommendation.listFilterRules();
		expect(last()).toMatchObject({ path: '/filter-rules', method: 'GET' });
	});

	it.each(['BOOST', 'MUTE'] as const)('adds a %s rule with its term', async (mode) => {
		const { recommendation, last } = api([{ id: 'rule-1' }]);
		await recommendation.addFilterRule('crypto', mode);
		expect(last()).toMatchObject({
			path: '/filter-rules',
			method: 'POST',
			body: { term: 'crypto', mode }
		});
	});

	it('deletes one by id', async () => {
		const { recommendation, last } = api([undefined]);
		await recommendation.deleteFilterRule('rule-1');
		expect(last()).toMatchObject({ path: '/filter-rules/rule-1', method: 'DELETE' });
	});
});
