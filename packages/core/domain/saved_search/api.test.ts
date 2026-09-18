import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createSavedSearchApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, savedSearch: createSavedSearchApi(recorder.http) };
}

describe('listSavedSearches', () => {
	it('returns whatever the backend answered', async () => {
		const { savedSearch } = api([[{ id: 'search-1' }]]);
		await expect(savedSearch.listSavedSearches()).resolves.toEqual([{ id: 'search-1' }]);
	});
});

describe('createSavedSearch', () => {
	it('sends the name, the filters and the alert flag', async () => {
		const { savedSearch, last } = api([{ id: 'search-1' }]);
		await savedSearch.createSavedSearch('Rust news', { query: 'rust', feedId: 'feed-1' }, true);
		expect(last()).toMatchObject({
			path: '/saved-searches',
			method: 'POST',
			body: { name: 'Rust news', query: 'rust', feed_id: 'feed-1', is_alert: true }
		});
	});

	it('defaults to a plain, non-alerting saved search', async () => {
		const { savedSearch, last } = api([{ id: 'search-1' }]);
		await savedSearch.createSavedSearch('Everything');
		expect(last()).toMatchObject({ body: { name: 'Everything', is_alert: false } });
	});
});

describe('updateSavedSearch', () => {
	it('sends only the name when renaming, leaving the filters alone', async () => {
		const { savedSearch, last } = api([{ id: 'search-1' }]);
		await savedSearch.updateSavedSearch('search-1', { name: 'New name' });
		expect(last()).toMatchObject({
			path: '/saved-searches/search-1',
			method: 'PATCH',
			body: { name: 'New name' }
		});
		expect(last().body).not.toHaveProperty('query');
	});

	it('sends the alert flag on its own', async () => {
		const { savedSearch, last } = api([{ id: 'search-1' }]);
		await savedSearch.updateSavedSearch('search-1', { isAlert: true });
		expect(last().body).toEqual({ is_alert: true });
	});
});

describe('deleteSavedSearch', () => {
	it('deletes by id', async () => {
		const { savedSearch, last } = api([undefined]);
		await savedSearch.deleteSavedSearch('search-1');
		expect(last()).toMatchObject({ path: '/saved-searches/search-1', method: 'DELETE' });
	});
});
