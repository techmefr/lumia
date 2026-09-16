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

/**
 * What a bulk action applies to. Exactly one of the four must be set: the backend answers 422
 * otherwise, so a forgotten filter can never widen an action to the whole library.
 */
export interface ArticleScope {
	article_ids?: string[];
	feed_id?: string;
	folder_id?: string;
	/** Every article across every feed, not just the ones currently loaded on screen. */
	all?: boolean;
}

export interface Keyword {
	id: string;
	term: string;
}

export interface ArticleDetail extends ArticleSummary {
	content: string;
	keywords: Keyword[];
}

export interface ArticleTranslation {
	target_lang: string;
	title: string;
	content: string;
}
