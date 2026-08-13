import type { HttpClient } from '../../technical/http-client';
import type { ArticleDetail, ArticleSummary } from './types';

export interface ListArticlesParams {
	folderId?: string;
	feedId?: string;
	authorId?: string;
	categoryId?: string;
	keywordId?: string;
	limit?: number;
	offset?: number;
}

function toQueryString(params: Record<string, string | number | undefined>): string {
	const query = new URLSearchParams();
	for (const [key, value] of Object.entries(params)) {
		if (value !== undefined) query.set(key, String(value));
	}
	const serialized = query.toString();
	return serialized ? `?${serialized}` : '';
}

export function createArticleApi(http: HttpClient) {
	async function listArticles(params: ListArticlesParams = {}): Promise<ArticleSummary[]> {
		const suffix = toQueryString({
			folder_id: params.folderId,
			feed_id: params.feedId,
			author_id: params.authorId,
			category_id: params.categoryId,
			keyword_id: params.keywordId,
			limit: params.limit,
			offset: params.offset
		});
		return http.request<ArticleSummary[]>(`/articles${suffix}`);
	}

	async function getArticle(articleId: string): Promise<ArticleDetail> {
		return http.request<ArticleDetail>(`/articles/${articleId}`);
	}

	return { listArticles, getArticle };
}

export type ArticleApi = ReturnType<typeof createArticleApi>;
