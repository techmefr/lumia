import { ApiError, type ArticleDetail, type ArticleSummary } from '@lumia/core';
import { getStoredArticle, listStoredArticles } from './article-store';
import { isOfflineStorageAvailable } from './offline-db';

function isNetworkFailure(error: unknown): boolean {
	return !(error instanceof ApiError) && isOfflineStorageAvailable();
}

export async function readArticle(
	fetchArticle: () => Promise<ArticleDetail>,
	articleId: string
): Promise<ArticleDetail> {
	try {
		return await fetchArticle();
	} catch (error) {
		if (!isNetworkFailure(error)) throw error;
		const stored = await getStoredArticle(articleId);
		if (!stored) throw error;
		return stored.article;
	}
}

export interface SavedListing {
	articles: ArticleSummary[];
	offline: boolean;
}

export async function readSavedList(
	fetchSaved: () => Promise<ArticleSummary[]>
): Promise<SavedListing> {
	try {
		return { articles: await fetchSaved(), offline: false };
	} catch (error) {
		if (!isNetworkFailure(error)) throw error;
		const stored = await listStoredArticles('saved');
		if (stored.length === 0) throw error;
		return { articles: stored.map((entry) => entry.article), offline: true };
	}
}
