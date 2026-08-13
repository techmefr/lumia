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

/** Unread totals keyed by feed id and by folder id, as returned by /feeds/unread-counts. */
export interface UnreadCounts {
	total: number;
	feeds: Record<string, number>;
	folders: Record<string, number>;
}
