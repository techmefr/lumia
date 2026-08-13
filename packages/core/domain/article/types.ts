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
}

export interface Keyword {
	id: string;
	term: string;
}

export interface ArticleDetail extends ArticleSummary {
	content: string;
	keywords: Keyword[];
}
