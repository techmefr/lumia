import type { ArticleSummary } from '../article/types';

/** What an account may do on a playlist; the owner is the one who made it. */
export type PlaylistRole = 'owner' | 'editor' | 'viewer';

/** The role a playlist can be shared with: the owner is never granted. */
export type PlaylistMemberRole = 'editor' | 'viewer';

export interface PlaylistSummary {
	id: string;
	name: string;
	role: PlaylistRole;
	owner_name: string;
	item_count: number;
	total_reading_minutes: number;
}

export interface PlaylistItemAuthorship {
	article_id: string;
	/** Null for an item added before playlists could be shared. */
	added_by: string | null;
}

export interface PlaylistDetail {
	id: string;
	name: string;
	role: PlaylistRole;
	owner_name: string;
	articles: ArticleSummary[];
	authorship: PlaylistItemAuthorship[];
}

export interface PlaylistMember {
	user_id: string;
	username: string;
	role: PlaylistMemberRole;
}

export interface PlaylistMembers {
	owner_name: string;
	members: PlaylistMember[];
}

export interface PlaylistBulkItemsResult {
	moved: number;
	/** Only the articles that actually moved, which is what an undo must revert. */
	article_ids: string[];
}

export type ExportStatus = 'pending' | 'ready' | 'failed';

export interface ExportJob {
	id: string;
	kind: 'playlist_epub';
	status: ExportStatus;
	file_name: string | null;
}
