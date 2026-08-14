import type { HttpClient } from '../../technical/http-client';
import type { PlaylistDetail, PlaylistSummary } from './types';

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
		reorder
	};
}

export type PlaylistApi = ReturnType<typeof createPlaylistApi>;
