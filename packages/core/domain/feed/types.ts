export type SourceType = 'miniflux' | 'manual';

export interface Folder {
	id: string;
	name: string;
}

export interface Feed {
	id: string;
	folder_id: string | null;
	source_type: SourceType;
	external_feed_id: string;
	title: string;
	url: string;
}

/** A source from the bundled catalogue the reader is not subscribed to yet. */
export interface DiscoverSuggestion {
	title: string;
	url: string;
	site_url: string;
	description: string;
	language: string;
	topics: string[];
	/** null while nothing has been learned about the reader's tastes. */
	affinity: number | null;
}

/** Unread totals keyed by feed id and by folder id, as returned by /feeds/unread-counts. */
export interface UnreadCounts {
	total: number;
	feeds: Record<string, number>;
	folders: Record<string, number>;
}
