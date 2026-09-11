import type { HttpClient } from '../../technical/http-client';
import type { DiscoverSuggestion, Feed, Folder, UnreadCounts } from './types';

export interface FeedUpdate {
	title?: string;
	/** Explicit null unfiles the feed; omitting the key leaves it where it is. */
	folder_id?: string | null;
}

export function createFeedApi(http: HttpClient) {
	async function listFolders(): Promise<Folder[]> {
		return http.request<Folder[]>('/folders');
	}

	async function createFolder(name: string): Promise<Folder> {
		return http.request<Folder>('/folders', { method: 'POST', body: { name } });
	}

	async function renameFolder(folderId: string, name: string): Promise<Folder> {
		return http.request<Folder>(`/folders/${folderId}`, { method: 'PATCH', body: { name } });
	}

	/** Deleting a folder unfiles its feeds on the backend; it never deletes them. */
	async function deleteFolder(folderId: string): Promise<void> {
		await http.request(`/folders/${folderId}`, { method: 'DELETE' });
	}

	async function listFeeds(): Promise<Feed[]> {
		return http.request<Feed[]>('/feeds');
	}

	async function updateFeed(feedId: string, update: FeedUpdate): Promise<Feed> {
		return http.request<Feed>(`/feeds/${feedId}`, { method: 'PATCH', body: update });
	}

	async function deleteFeed(feedId: string): Promise<void> {
		await http.request(`/feeds/${feedId}`, { method: 'DELETE' });
	}

	/** Asks the backend to re-fetch this feed from its provider right away. */
	async function refreshFeed(feedId: string): Promise<Feed> {
		return http.request<Feed>(`/feeds/${feedId}/refresh`, { method: 'POST' });
	}

	async function getUnreadCounts(): Promise<UnreadCounts> {
		return http.request<UnreadCounts>('/feeds/unread-counts');
	}

	async function addFeedByUrl(url: string, folderId?: string | null): Promise<Feed> {
		return http.request<Feed>('/feeds/add-by-url', {
			method: 'POST',
			body: { url, folder_id: folderId ?? null }
		});
	}

	/** Uploads a Feedly OPML export; the backend creates one folder per category and registers each feed. */
	async function importOpml(file: File): Promise<Feed[]> {
		const formData = new FormData();
		formData.append('file', file);
		return http.request<Feed[]>('/feeds/import-opml', { method: 'POST', formData });
	}

	/** The reader's own folders and feeds, rebuilt as an OPML document they can take elsewhere. */
	async function exportOpml(): Promise<Blob> {
		return http.requestBlob('/feeds/export-opml');
	}

	async function discoverFeeds(limit = 6): Promise<DiscoverSuggestion[]> {
		return http.request<DiscoverSuggestion[]>(`/feeds/discover?limit=${limit}`);
	}

	return {
		discoverFeeds,
		listFolders,
		createFolder,
		renameFolder,
		deleteFolder,
		listFeeds,
		updateFeed,
		deleteFeed,
		refreshFeed,
		getUnreadCounts,
		importOpml,
		exportOpml,
		addFeedByUrl
	};
}

export type FeedApi = ReturnType<typeof createFeedApi>;
