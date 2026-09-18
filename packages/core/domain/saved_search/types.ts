/** The same filters `GET /articles` accepts, given a name and a place to live. */
export interface SavedSearchFilters {
	query?: string | null;
	folderId?: string | null;
	feedId?: string | null;
	authorId?: string | null;
	categoryId?: string | null;
	keywordId?: string | null;
}

export interface SavedSearch {
	id: string;
	name: string;
	query: string | null;
	folder_id: string | null;
	feed_id: string | null;
	author_id: string | null;
	category_id: string | null;
	keyword_id: string | null;
	/** Whether the worker mails the reader when a newly ingested article matches. */
	is_alert: boolean;
	/** How many currently-unread articles this saved search would return right now. */
	unread_count: number;
}

export interface SavedSearchUpdate {
	name?: string;
	isAlert?: boolean;
	filters?: SavedSearchFilters;
}
