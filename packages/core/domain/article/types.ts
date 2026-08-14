export interface ArticleSummary {
	id: string;
	feed_id: string;
	author_id: string | null;
	author_name: string | null;
	category_id: string | null;
	category_name: string | null;
	source_label: string;
	title: string;
	url: string;
	summary: string | null;
	image_url: string | null;
	published_at: string;
	/** Estimated minutes to read, from the backend's word count. Always at least 1. */
	reading_minutes: number;
	read: boolean;
	/** How far the user got, 0 to 1. */
	scroll_progress: number;
	/** 0 to 100 affinity, 50 meaning nothing has been learned about this article yet. */
	relevance_score: number;
}

export interface Keyword {
	id: string;
	term: string;
}

export interface ArticleDetail extends ArticleSummary {
	content: string;
	keywords: Keyword[];
}
