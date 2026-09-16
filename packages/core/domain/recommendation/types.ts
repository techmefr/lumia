import type { ArticleScope } from '../article/types';

export type Vote = 'like' | 'dislike';

export interface FeedbackUpdate {
	sentiment?: Vote | null;
	saved?: boolean;
	favorite?: boolean;
	read?: boolean;
	/** 0 to 1. The backend keeps the highest value seen, so it never rewinds. */
	scroll_progress?: number;
}

export type FilterMode = 'boost' | 'mute';

export interface FilterRule {
	id: string;
	/** Always lowercase: the backend normalises before storing. */
	term: string;
	mode: FilterMode;
}

/** Exactly one scope must be set: the backend rejects zero or several with a 422. */
export interface MarkReadScope extends ArticleScope {
	read?: boolean;
}

/**
 * The feedback axes a bulk action can touch. One per call: they are independent, and favouriting
 * a selection says nothing about having read it.
 */
export type FeedbackAxis = 'read' | 'saved' | 'favorite';

export interface BulkFeedbackRequest extends ArticleScope {
	axis: FeedbackAxis;
	value?: boolean;
}

export interface BulkFeedbackResult {
	/** How many articles the scope covered. */
	updated: number;
	/** Only those that did not already hold the value — exactly what an undo has to revert. */
	changed_article_ids: string[];
}
