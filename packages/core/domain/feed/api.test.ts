import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createFeedApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, feeds: createFeedApi(recorder.http) };
}

describe('folders', () => {
	it('lists them', async () => {
		const { feeds, last } = api([[{ id: 'folder-1', name: 'Tech' }]]);
		await expect(feeds.listFolders()).resolves.toEqual([{ id: 'folder-1', name: 'Tech' }]);
		expect(last()).toMatchObject({ path: '/folders', method: 'GET' });
	});

	it('creates one from a name', async () => {
		const { feeds, last } = api([{ id: 'folder-2' }]);
		await feeds.createFolder('Science');
		expect(last()).toMatchObject({ path: '/folders', method: 'POST', body: { name: 'Science' } });
	});

	it('renames one in place', async () => {
		const { feeds, last } = api([{ id: 'folder-2' }]);
		await feeds.renameFolder('folder-2', 'Sciences');
		expect(last()).toMatchObject({
			path: '/folders/folder-2',
			method: 'PATCH',
			body: { name: 'Sciences' }
		});
	});

	it('deletes one', async () => {
		const { feeds, last } = api([undefined]);
		await feeds.deleteFolder('folder-2');
		expect(last()).toMatchObject({ path: '/folders/folder-2', method: 'DELETE' });
	});
});

describe('feeds', () => {
	it('lists them', async () => {
		const { feeds, last } = api([[]]);
		await feeds.listFeeds();
		expect(last()).toMatchObject({ path: '/feeds', method: 'GET' });
	});

	it('renames one without touching its folder', async () => {
		const { feeds, last } = api([{ id: 'feed-1' }]);
		await feeds.updateFeed('feed-1', { title: 'Atelier Papier' });
		expect(last().body).toEqual({ title: 'Atelier Papier' });
	});

	// The distinction the type documents: an explicit null unfiles, an absent key leaves it alone.
	it('unfiles one with an explicit null folder', async () => {
		const { feeds, last } = api([{ id: 'feed-1' }]);
		await feeds.updateFeed('feed-1', { folder_id: null });
		expect(last().body).toEqual({ folder_id: null });
	});

	it('deletes one', async () => {
		const { feeds, last } = api([undefined]);
		await feeds.deleteFeed('feed-1');
		expect(last()).toMatchObject({ path: '/feeds/feed-1', method: 'DELETE' });
	});

	it('reads the unread counts from their own endpoint', async () => {
		const { feeds, last } = api([{ total: 9, feeds: {}, folders: {} }]);
		await expect(feeds.getUnreadCounts()).resolves.toMatchObject({ total: 9 });
		expect(last().path).toBe('/feeds/unread-counts');
	});

	it('asks for an immediate refresh of one feed', async () => {
		const { feeds, last } = api([{ id: 'feed-1', error_count: 0 }]);
		await expect(feeds.refreshFeed('feed-1')).resolves.toMatchObject({ error_count: 0 });
		expect(last()).toMatchObject({ path: '/feeds/feed-1/refresh', method: 'POST' });
	});
});

describe('addFeedByUrl', () => {
	it('files the feed into the folder it was given', async () => {
		const { feeds, last } = api([{ id: 'feed-2' }]);
		await feeds.addFeedByUrl('https://blog.test/rss', 'folder-1');
		expect(last()).toMatchObject({
			path: '/feeds/add-by-url',
			method: 'POST',
			body: { url: 'https://blog.test/rss', folder_id: 'folder-1' }
		});
	});

	it('sends an explicit null when no folder was chosen, rather than omitting the key', async () => {
		const { feeds, last } = api([{ id: 'feed-2' }]);
		await feeds.addFeedByUrl('https://blog.test/rss');
		expect(last().body).toEqual({ url: 'https://blog.test/rss', folder_id: null });
	});
});

describe('importOpml', () => {
	it('uploads the file as multipart under the name the backend reads', async () => {
		const { feeds, last } = api([[]]);
		const file = new File(['<opml />'], 'feedly.opml', { type: 'text/xml' });
		await feeds.importOpml(file);
		expect(last()).toMatchObject({ path: '/feeds/import-opml', method: 'POST' });
		expect(last().formData?.get('file')).toBe(file);
	});

	it('sends no json body, which would clash with the upload', async () => {
		const { feeds, last } = api([[]]);
		await feeds.importOpml(new File(['<opml />'], 'feedly.opml'));
		expect(last().body).toBeUndefined();
	});
});

describe('exportOpml', () => {
	it('fetches the export as a file rather than json', async () => {
		const blob = new Blob(['<opml />'], { type: 'text/x-opml' });
		const { feeds, last } = api([blob]);
		await expect(feeds.exportOpml()).resolves.toBe(blob);
		expect(last()).toMatchObject({ path: '/feeds/export-opml', method: 'GET' });
	});
});

describe('discoverFeeds', () => {
	it('asks for six suggestions by default', async () => {
		const { feeds, last } = api([[]]);
		await feeds.discoverFeeds();
		expect(last().path).toBe('/feeds/discover?limit=6');
	});

	it('honours an explicit limit', async () => {
		const { feeds, last } = api([[]]);
		await feeds.discoverFeeds(20);
		expect(last().path).toBe('/feeds/discover?limit=20');
	});
});
