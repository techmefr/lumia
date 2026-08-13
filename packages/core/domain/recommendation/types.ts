export type Vote = 'like' | 'dislike';

export interface FeedbackUpdate {
	sentiment?: Vote | null;
	saved?: boolean;
	favorite?: boolean;
}
