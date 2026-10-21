import type { HttpClient } from '../../technical/http-client';
import type {
	ArticleDetail,
	ArticleShareCreated,
	ArticleShareStatus,
	ArticleSummary,
	ArticleTranslation,
	PublicArticle,
	ReadingListImportProgress,
	ReadingListImportStarted,
	ReadingListSource
} from './types';

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

	async function getRelatedArticles(articleId: string): Promise<ArticleSummary[]> {
		return http.request<ArticleSummary[]>(`/articles/${articleId}/related`);
	}

	/** Saves an arbitrary web page as a readable article on the user's "Enregistrés" feed. */
	async function saveUrl(url: string): Promise<ArticleSummary> {
		return http.request<ArticleSummary>('/articles/save-url', { method: 'POST', body: { url } });
	}

	/**
	 * Uploads a Pocket, Wallabag or Instapaper export. The backend only parses it and queues the
	 * links: the pages are fetched by the worker, so progress is read back with
	 * `getReadingListImportProgress`.
	 */
	async function importReadingList(
		source: ReadingListSource,
		file: File
	): Promise<ReadingListImportStarted> {
		const formData = new FormData();
		formData.append('source', source);
		formData.append('file', file);
		return http.request<ReadingListImportStarted>('/articles/import-reading-list', {
			method: 'POST',
			formData
		});
	}

	async function getReadingListImportProgress(
		importId: string
	): Promise<ReadingListImportProgress> {
		return http.request<ReadingListImportProgress>(`/articles/import-reading-list/${importId}`);
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

	/** The article as an EPUB, pictures embedded, ready to hand to an e-reader. */
	async function exportArticleEpub(articleId: string): Promise<Blob> {
		return http.requestBlob(`/articles/${articleId}/export.epub`);
	}

	async function getShareStatus(articleId: string): Promise<ArticleShareStatus> {
		return http.request<ArticleShareStatus>(`/articles/${articleId}/share`);
	}

	/** Issues a new public link, retiring the previous one. The token comes back only here. */
	async function createShare(articleId: string): Promise<ArticleShareCreated> {
		return http.request<ArticleShareCreated>(`/articles/${articleId}/share`, { method: 'POST' });
	}

	async function revokeShare(articleId: string): Promise<void> {
		await http.request<void>(`/articles/${articleId}/share`, { method: 'DELETE' });
	}

	/** The one call a visitor makes: no session, the token in the path is the whole credential. */
	async function getPublicArticle(token: string): Promise<PublicArticle> {
		return http.request<PublicArticle>(`/public/articles/${encodeURIComponent(token)}`, {
			auth: false
		});
	}

	return {
		listArticles,
		getArticle,
		getRelatedArticles,
		saveUrl,
		importReadingList,
		getReadingListImportProgress,
		translateArticle,
		exportArticleEpub,
		getShareStatus,
		createShare,
		revokeShare,
		getPublicArticle
	};
}

export type ArticleApi = ReturnType<typeof createArticleApi>;
