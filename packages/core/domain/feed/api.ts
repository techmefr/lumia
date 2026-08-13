import type { HttpClient } from '../../technical/http-client';
import type { Feed, Folder } from './types';

export function createFeedApi(http: HttpClient) {
	async function listFolders(): Promise<Folder[]> {
		return http.request<Folder[]>('/folders');
	}

	async function createFolder(name: string): Promise<Folder> {
		return http.request<Folder>('/folders', { method: 'POST', body: { name } });
	}

	async function listFeeds(): Promise<Feed[]> {
		return http.request<Feed[]>('/feeds');
	}

	async function deleteFeed(feedId: string): Promise<void> {
		await http.request(`/feeds/${feedId}`, { method: 'DELETE' });
	}

	/** Uploads a Feedly OPML export; the backend creates one folder per category and registers each feed. */
	async function importOpml(file: File): Promise<Feed[]> {
		const formData = new FormData();
		formData.append('file', file);
		return http.request<Feed[]>('/feeds/import-opml', { method: 'POST', formData });
	}

	return { listFolders, createFolder, listFeeds, deleteFeed, importOpml };
}

export type FeedApi = ReturnType<typeof createFeedApi>;
