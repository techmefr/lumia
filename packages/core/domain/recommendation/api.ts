import type { HttpClient } from '../../technical/http-client';
import type { ArticleSummary } from '../article/types';
import type { Vote } from './types';

export function createRecommendationApi(http: HttpClient) {
	async function getEtincelle(limit = 20, offset = 0): Promise<ArticleSummary[]> {
		return http.request<ArticleSummary[]>(`/articles/etincelle?limit=${limit}&offset=${offset}`);
	}

	async function sendFeedback(articleId: string, vote: Vote): Promise<void> {
		await http.request(`/articles/${articleId}/feedback`, { method: 'POST', body: { vote } });
	}

	return { getEtincelle, sendFeedback };
}

export type RecommendationApi = ReturnType<typeof createRecommendationApi>;
