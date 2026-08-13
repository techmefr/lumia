export type Vote = 'like' | 'dislike';

export interface FeedbackUpdate {
	sentiment?: Vote | null;
	saved?: boolean;
	favorite?: boolean;
	read?: boolean;
	/** 0 to 1. The backend keeps the highest value seen, so it never rewinds. */
	scroll_progress?: number;
}

/** Exactly one scope must be set: the backend rejects zero or several with a 422. */
export interface MarkReadScope {
	article_ids?: string[];
	feed_id?: string;
	folder_id?: string;
	read?: boolean;
}
