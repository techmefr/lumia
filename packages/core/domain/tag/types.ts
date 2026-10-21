export interface TagRef {
	id: string;
	name: string;
}

export interface Tag extends TagRef {
	/** How many articles carry it, shown before a rename or a delete. */
	article_count: number;
}

/**
 * Where a suggestion came from. `keyword` is the worker's own extraction, `used` a tag the reader
 * already has, `ai` the account's model. Always a suggestion: accepting it is the reader's call.
 */
export type TagSuggestionSource = 'keyword' | 'used' | 'ai';

export interface TagSuggestion {
	name: string;
	source: TagSuggestionSource;
}
