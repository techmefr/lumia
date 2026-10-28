import type { TagRef } from '../tag/types';

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
	/** Audio file of a podcast episode, streamed by the browser from its source; null for an ordinary article. */
	enclosure_url: string | null;
	enclosure_type: string | null;
	published_at: string;
	/** Estimated minutes to read, from the backend's word count. Always at least 1. */
	reading_minutes: number;
	read: boolean;
	/** How far the user got, 0 to 1. */
	scroll_progress: number;
	/** 0 to 100 affinity, 50 meaning nothing has been learned about this article yet. */
	relevance_score: number;
	/** The reader's own tags. They never feed the relevance score. */
	tags: TagRef[];
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

export interface SavedArticle extends ArticleSummary {
	already_saved?: boolean;
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

export interface ArticleShareStatus {
	/** Whether the instance admin allows public links at all. */
	enabled: boolean;
	/** Whether the article has a live link right now. */
	shared: boolean;
	created_at: string | null;
}

export interface ArticleShareCreated {
	/** Shown once: the backend keeps only a hash, so a lost link is replaced rather than recovered. */
	token: string;
	created_at: string;
}

/** What a public link opens. Deliberately no feed, account or article id. */
export interface PublicArticle {
	title: string;
	/** Sanitized by the backend before it leaves the instance. */
	content: string;
	url: string;
	published_at: string;
	author_name: string | null;
	image_url: string | null;
	language: string;
}

export type ReadingListSource = 'pocket' | 'wallabag' | 'instapaper';

export interface ReadingListImportStarted {
	import_id: string;
	total: number;
}

export interface ReadingListImportProgress {
	total: number;
	saved: number;
	failed: number;
	finished: boolean;
}
