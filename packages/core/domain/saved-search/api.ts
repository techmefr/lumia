import type { HttpClient } from '../../technical/http-client';
import type {
	AlertNotificationList,
	SavedSearch,
	SavedSearchCreate,
	SavedSearchUpdate
} from './types';

export function createSavedSearchApi(http: HttpClient) {
	async function listSavedSearches(): Promise<SavedSearch[]> {
		return http.request<SavedSearch[]>('/saved-searches');
	}

	async function createSavedSearch(search: SavedSearchCreate): Promise<SavedSearch> {
		return http.request<SavedSearch>('/saved-searches', { method: 'POST', body: search });
	}

	async function updateSavedSearch(
		searchId: string,
		update: SavedSearchUpdate
	): Promise<SavedSearch> {
		return http.request<SavedSearch>(`/saved-searches/${searchId}`, {
			method: 'PATCH',
			body: update
		});
	}

	async function deleteSavedSearch(searchId: string): Promise<void> {
		await http.request(`/saved-searches/${searchId}`, { method: 'DELETE' });
	}

	async function listNotifications(limit = 30, offset = 0): Promise<AlertNotificationList> {
		return http.request<AlertNotificationList>(`/notifications?limit=${limit}&offset=${offset}`);
	}

	/** Marks the given notifications read, or every unread one when no ids are passed. */
	async function markNotificationsRead(ids?: string[]): Promise<void> {
		await http.request('/notifications/mark-read', {
			method: 'POST',
			body: ids === undefined ? {} : { ids }
		});
	}

	return {
		listSavedSearches,
		createSavedSearch,
		updateSavedSearch,
		deleteSavedSearch,
		listNotifications,
		markNotificationsRead
	};
}

export type SavedSearchApi = ReturnType<typeof createSavedSearchApi>;
