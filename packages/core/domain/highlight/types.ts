/**
 * Where a highlight sits in an article, without a DOM path: the passage, a little text around it,
 * and its offset in the article's flattened text. The offset is a hint, the quote and its context
 * are what finds the passage again once the content has been extracted or sanitised anew.
 */
export interface HighlightAnchor {
	quote: string;
	prefix: string;
	suffix: string;
	start_offset: number;
	end_offset: number;
}

export interface Highlight extends HighlightAnchor {
	id: string;
	article_id: string;
	article_title: string;
	note: string | null;
	created_at: string;
}

export interface HighlightDraft extends HighlightAnchor {
	note?: string | null;
}
