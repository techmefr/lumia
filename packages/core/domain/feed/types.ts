export type SourceType = 'miniflux';

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
