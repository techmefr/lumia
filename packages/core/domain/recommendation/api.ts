import type { HttpClient } from '../../technical/http-client';
import type { ArticleSummary } from '../article/types';
import type { FeedbackUpdate } from './types';

export function createRecommendationApi(http: HttpClient) {
	async function getEtincelle(limit = 20, offset = 0): Promise<ArticleSummary[]> {
		return http.request<ArticleSummary[]>(`/articles/etincelle?limit=${limit}&offset=${offset}`);
	}

	async function getSaved(limit = 20, offset = 0): Promise<ArticleSummary[]> {
		return http.request<ArticleSummary[]>(`/articles/saved?limit=${limit}&offset=${offset}`);
	}

	async function getFavorites(limit = 20, offset = 0): Promise<ArticleSummary[]> {
		return http.request<ArticleSummary[]>(`/articles/favorites?limit=${limit}&offset=${offset}`);
	}

	async function sendFeedback(articleId: string, update: FeedbackUpdate): Promise<void> {
		await http.request(`/articles/${articleId}/feedback`, { method: 'POST', body: update });
	}

	return { getEtincelle, getSaved, getFavorites, sendFeedback };
}

export type RecommendationApi = ReturnType<typeof createRecommendationApi>;
