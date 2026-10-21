export interface SavedSearch {
	id: string;
	name: string;
	/** The same free text `GET /articles?q=` takes. */
	query: string;
	feed_id: string | null;
	folder_id: string | null;
	/** When true the worker checks each new article against this search and notifies. */
	alert: boolean;
	/** Articles matching the search that the reader has not read yet. */
	unread_count: number;
}

export interface SavedSearchCreate {
	name: string;
	query: string;
	feed_id?: string;
	folder_id?: string;
	alert?: boolean;
}

export interface SavedSearchUpdate {
	name?: string;
	alert?: boolean;
}

export interface AlertNotification {
	id: string;
	saved_search_id: string;
	saved_search_name: string;
	article_id: string;
	article_title: string;
	read: boolean;
	created_at: string;
}

export interface AlertNotificationList {
	/** Across every page, not just the one returned. */
	unread_count: number;
	items: AlertNotification[];
}
