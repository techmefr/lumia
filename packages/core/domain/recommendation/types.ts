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

export interface DailyReading {
	/** The reader's local calendar day, YYYY-MM-DD. */
	day: string;
	articles_read: number;
	reading_minutes: number;
}

export interface RankedSource {
	id: string;
	name: string;
	articles_read: number;
}

export interface RankedKeyword {
	term: string;
	articles_read: number;
}

/** What a feed delivered over the period against what was read of it. */
export interface FeedEngagement {
	feed_id: string;
	title: string;
	received: number;
	read: number;
	ignored: number;
	/** 0 to 1. */
	read_ratio: number;
}

export interface FeedbackTotals {
	saved: number;
	favorites: number;
	liked: number;
	disliked: number;
}

export interface ReadingStatistics {
	period_days: number;
	articles_read: number;
	reading_minutes: number;
	/** One entry per day of the period, empty days included, oldest first. */
	daily: DailyReading[];
	top_feeds: RankedSource[];
	top_authors: RankedSource[];
	top_keywords: RankedKeyword[];
	/** Least read first. */
	feed_engagement: FeedEngagement[];
	totals: FeedbackTotals;
}

export interface PopularArticle {
	title: string;
	url: string;
	readers: number;
}

/** Aggregate counts only: no reader is ever named, and rows under min_readers are not sent. */
export interface Popularity {
	period_days: number;
	min_readers: number;
	articles: PopularArticle[];
}
