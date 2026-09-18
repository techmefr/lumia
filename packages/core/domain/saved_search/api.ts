import type { HttpClient } from '../../technical/http-client';
import type { SavedSearch, SavedSearchFilters, SavedSearchUpdate } from './types';

function filtersPayload(filters: SavedSearchFilters = {}) {
	return {
		query: filters.query,
		folder_id: filters.folderId,
		feed_id: filters.feedId,
		author_id: filters.authorId,
		category_id: filters.categoryId,
		keyword_id: filters.keywordId
	};
}

export function createSavedSearchApi(http: HttpClient) {
	async function listSavedSearches(): Promise<SavedSearch[]> {
		return http.request<SavedSearch[]>('/saved-searches');
	}

	async function createSavedSearch(
		name: string,
		filters: SavedSearchFilters = {},
		isAlert = false
	): Promise<SavedSearch> {
		return http.request<SavedSearch>('/saved-searches', {
			method: 'POST',
			body: { name, is_alert: isAlert, ...filtersPayload(filters) }
		});
	}

	/** Only the fields actually set on `update` are sent, so a rename never touches the filters. */
	async function updateSavedSearch(
		savedSearchId: string,
		update: SavedSearchUpdate
	): Promise<SavedSearch> {
		const body: Record<string, unknown> = {};
		if (update.name !== undefined) body.name = update.name;
		if (update.isAlert !== undefined) body.is_alert = update.isAlert;
		if (update.filters !== undefined) Object.assign(body, filtersPayload(update.filters));
		return http.request<SavedSearch>(`/saved-searches/${savedSearchId}`, {
			method: 'PATCH',
			body
		});
	}

	async function deleteSavedSearch(savedSearchId: string): Promise<void> {
		await http.request(`/saved-searches/${savedSearchId}`, { method: 'DELETE' });
	}

	return { listSavedSearches, createSavedSearch, updateSavedSearch, deleteSavedSearch };
}

export type SavedSearchApi = ReturnType<typeof createSavedSearchApi>;
