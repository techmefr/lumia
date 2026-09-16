import type { HttpClient } from '../../technical/http-client';
import type { ArticleScope } from '../article/types';
import type { PlaylistBulkItemsResult, PlaylistDetail, PlaylistSummary } from './types';

export function createPlaylistApi(http: HttpClient) {
	async function listPlaylists(): Promise<PlaylistSummary[]> {
		return http.request<PlaylistSummary[]>('/playlists');
	}

	async function createPlaylist(name: string): Promise<PlaylistSummary> {
		return http.request<PlaylistSummary>('/playlists', { method: 'POST', body: { name } });
	}

	/** Fills a fresh playlist with the best-scored unread articles that fit the given minutes. */
	async function createPlaylistForDuration(targetMinutes: number): Promise<PlaylistDetail> {
		return http.request<PlaylistDetail>('/playlists/for-duration', {
			method: 'POST',
			body: { target_minutes: targetMinutes }
		});
	}

	async function getPlaylist(playlistId: string): Promise<PlaylistDetail> {
		return http.request<PlaylistDetail>(`/playlists/${playlistId}`);
	}

	async function renamePlaylist(playlistId: string, name: string): Promise<PlaylistSummary> {
		return http.request<PlaylistSummary>(`/playlists/${playlistId}`, {
			method: 'PATCH',
			body: { name }
		});
	}

	async function deletePlaylist(playlistId: string): Promise<void> {
		await http.request(`/playlists/${playlistId}`, { method: 'DELETE' });
	}

	async function addArticle(playlistId: string, articleId: string): Promise<PlaylistDetail> {
		return http.request<PlaylistDetail>(`/playlists/${playlistId}/items`, {
			method: 'POST',
			body: { article_id: articleId }
		});
	}

	async function removeArticle(playlistId: string, articleId: string): Promise<PlaylistDetail> {
		return http.request<PlaylistDetail>(`/playlists/${playlistId}/items/${articleId}`, {
			method: 'DELETE'
		});
	}

	/**
	 * Puts a whole scope of articles in or out of the playlist, in one request. `present` false is
	 * what an undo sends back, carrying the ids the add actually moved.
	 */
	async function bulkSetItems(
		playlistId: string,
		scope: ArticleScope,
		present = true
	): Promise<PlaylistBulkItemsResult> {
		return http.request<PlaylistBulkItemsResult>(`/playlists/${playlistId}/items/bulk`, {
			method: 'POST',
			body: { ...scope, present }
		});
	}

	/** Sends the full desired order; ids left out keep their relative place at the end. */
	async function reorder(playlistId: string, articleIds: string[]): Promise<PlaylistDetail> {
		return http.request<PlaylistDetail>(`/playlists/${playlistId}/order`, {
			method: 'PUT',
			body: { article_ids: articleIds }
		});
	}

	return {
		listPlaylists,
		createPlaylist,
		createPlaylistForDuration,
		getPlaylist,
		renamePlaylist,
		deletePlaylist,
		addArticle,
		removeArticle,
		bulkSetItems,
		reorder
	};
}

export type PlaylistApi = ReturnType<typeof createPlaylistApi>;
