import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createPlaylistApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, playlists: createPlaylistApi(recorder.http) };
}

describe('the collection', () => {
	it('lists the playlists', async () => {
		const { playlists, last } = api([[{ id: 'playlist-1' }]]);
		await expect(playlists.listPlaylists()).resolves.toEqual([{ id: 'playlist-1' }]);
		expect(last()).toMatchObject({ path: '/playlists', method: 'GET' });
	});

	it('creates an empty one from a name', async () => {
		const { playlists, last } = api([{ id: 'playlist-2' }]);
		await playlists.createPlaylist('Trajet du matin');
		expect(last()).toMatchObject({
			path: '/playlists',
			method: 'POST',
			body: { name: 'Trajet du matin' }
		});
	});

	it('fills one to a target duration in minutes', async () => {
		const { playlists, last } = api([{ id: 'playlist-3' }]);
		await playlists.createPlaylistForDuration(25);
		expect(last()).toMatchObject({
			path: '/playlists/for-duration',
			method: 'POST',
			body: { target_minutes: 25 }
		});
	});

	it('reads one by id', async () => {
		const { playlists, last } = api([{ id: 'playlist-1', items: [] }]);
		await playlists.getPlaylist('playlist-1');
		expect(last()).toMatchObject({ path: '/playlists/playlist-1', method: 'GET' });
	});

	it('renames one', async () => {
		const { playlists, last } = api([{ id: 'playlist-1' }]);
		await playlists.renamePlaylist('playlist-1', 'Trajet du soir');
		expect(last()).toMatchObject({
			path: '/playlists/playlist-1',
			method: 'PATCH',
			body: { name: 'Trajet du soir' }
		});
	});

	it('deletes one', async () => {
		const { playlists, last } = api([undefined]);
		await playlists.deletePlaylist('playlist-1');
		expect(last()).toMatchObject({ path: '/playlists/playlist-1', method: 'DELETE' });
	});
});

describe('the items', () => {
	it('adds an article by id in the body, not in the path', async () => {
		const { playlists, last } = api([{ id: 'playlist-1' }]);
		await playlists.addArticle('playlist-1', 'article-7');
		expect(last()).toMatchObject({
			path: '/playlists/playlist-1/items',
			method: 'POST',
			body: { article_id: 'article-7' }
		});
	});

	it('removes an article by id in the path, with no body', async () => {
		const { playlists, last } = api([{ id: 'playlist-1' }]);
		await playlists.removeArticle('playlist-1', 'article-7');
		expect(last()).toMatchObject({
			path: '/playlists/playlist-1/items/article-7',
			method: 'DELETE',
			body: undefined
		});
	});

	it('replaces the whole order with a put, order preserved', async () => {
		const { playlists, last } = api([{ id: 'playlist-1' }]);
		await playlists.reorder('playlist-1', ['article-3', 'article-1', 'article-2']);
		expect(last()).toMatchObject({
			path: '/playlists/playlist-1/order',
			method: 'PUT',
			body: { article_ids: ['article-3', 'article-1', 'article-2'] }
		});
	});

	it('accepts an empty order, which is how a playlist is emptied', async () => {
		const { playlists, last } = api([{ id: 'playlist-1' }]);
		await playlists.reorder('playlist-1', []);
		expect(last().body).toEqual({ article_ids: [] });
	});
});
