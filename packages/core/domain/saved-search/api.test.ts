import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createSavedSearchApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, searches: createSavedSearchApi(recorder.http) };
}

describe('saved searches', () => {
	it('lists them', async () => {
		const { searches, last } = api([[{ id: 'search-1' }]]);
		await expect(searches.listSavedSearches()).resolves.toEqual([{ id: 'search-1' }]);
		expect(last()).toMatchObject({ path: '/saved-searches', method: 'GET' });
	});

	it('creates one with its scope and alert flag', async () => {
		const { searches, last } = api([{ id: 'search-1' }]);
		await searches.createSavedSearch({ name: 'Rust', query: 'rust', feed_id: 'feed-1', alert: true });
		expect(last()).toMatchObject({
			path: '/saved-searches',
			method: 'POST',
			body: { name: 'Rust', query: 'rust', feed_id: 'feed-1', alert: true }
		});
	});

	it('updates the name or the alert flag', async () => {
		const { searches, last } = api([{ id: 'search-1' }]);
		await searches.updateSavedSearch('search-1', { alert: true });
		expect(last()).toMatchObject({
			path: '/saved-searches/search-1',
			method: 'PATCH',
			body: { alert: true }
		});
	});

	it('deletes one', async () => {
		const { searches, last } = api([undefined]);
		await searches.deleteSavedSearch('search-1');
		expect(last()).toMatchObject({ path: '/saved-searches/search-1', method: 'DELETE' });
	});
});

describe('notifications', () => {
	it('lists the first page by default', async () => {
		const { searches, last } = api([{ unread_count: 0, items: [] }]);
		await searches.listNotifications();
		expect(last()).toMatchObject({ path: '/notifications?limit=30&offset=0', method: 'GET' });
	});

	it('lists a given page', async () => {
		const { searches, last } = api([{ unread_count: 0, items: [] }]);
		await searches.listNotifications(1, 5);
		expect(last()).toMatchObject({ path: '/notifications?limit=1&offset=5' });
	});

	it('marks the given ones read', async () => {
		const { searches, last } = api([undefined]);
		await searches.markNotificationsRead(['n1']);
		expect(last()).toMatchObject({
			path: '/notifications/mark-read',
			method: 'POST',
			body: { ids: ['n1'] }
		});
	});

	it('marks everything read when no id is given', async () => {
		const { searches, last } = api([undefined]);
		await searches.markNotificationsRead();
		expect(last()).toMatchObject({ path: '/notifications/mark-read', body: {} });
	});
});
