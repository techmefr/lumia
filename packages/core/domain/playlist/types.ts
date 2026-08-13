import type { ArticleSummary } from '../article/types';

export interface PlaylistSummary {
	id: string;
	name: string;
	item_count: number;
	total_reading_minutes: number;
}

export interface PlaylistDetail {
	id: string;
	name: string;
	articles: ArticleSummary[];
}
