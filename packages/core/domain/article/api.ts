import type { HttpClient } from '../../technical/http-client';
import type { ArticleDetail, ArticleSummary, ArticleTranslation } from './types';

export interface ListArticlesParams {
	folderId?: string;
	feedId?: string;
	authorId?: string;
	categoryId?: string;
	keywordId?: string;
	/** Free-text search over title, summary and content. Two characters minimum server-side. */
	query?: string;
	unreadOnly?: boolean;
	/** `relevance` ranks by learned affinity instead of publication date. */
	sort?: 'recent' | 'relevance';
	limit?: number;
	offset?: number;
}

function toQueryString(params: Record<string, string | number | boolean | undefined>): string {
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
			q: params.query,
			unread_only: params.unreadOnly ? true : undefined,
			sort: params.sort,
			limit: params.limit,
			offset: params.offset
		});
		return http.request<ArticleSummary[]>(`/articles${suffix}`);
	}

	async function getArticle(articleId: string): Promise<ArticleDetail> {
		return http.request<ArticleDetail>(`/articles/${articleId}`);
	}

	/** Saves an arbitrary web page as a readable article on the user's "Enregistrés" feed. */
	async function saveUrl(url: string): Promise<ArticleSummary> {
		return http.request<ArticleSummary>('/articles/save-url', { method: 'POST', body: { url } });
	}

	/**
	 * Translates one article on demand. Nothing is stored server-side, so the caller keeps the
	 * original text and can put it back.
	 */
	async function translateArticle(
		articleId: string,
		targetLang: string
	): Promise<ArticleTranslation> {
		return http.request<ArticleTranslation>(`/articles/${articleId}/translate`, {
			method: 'POST',
			body: { target_lang: targetLang }
		});
	}

	return { listArticles, getArticle, saveUrl, translateArticle };
}

export type ArticleApi = ReturnType<typeof createArticleApi>;
