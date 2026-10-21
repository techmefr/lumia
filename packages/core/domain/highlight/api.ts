import type { HttpClient } from '../../technical/http-client';
import type { Highlight, HighlightDraft } from './types';

export function createHighlightApi(http: HttpClient) {
	/** Every highlight of the reader, newest first. */
	async function listHighlights(): Promise<Highlight[]> {
		return http.request<Highlight[]>('/highlights');
	}

	async function listArticleHighlights(articleId: string): Promise<Highlight[]> {
		return http.request<Highlight[]>(`/articles/${articleId}/highlights`);
	}

	async function createHighlight(articleId: string, draft: HighlightDraft): Promise<Highlight> {
		return http.request<Highlight>(`/articles/${articleId}/highlights`, {
			method: 'POST',
			body: draft
		});
	}

	/** `null` clears the note; the passage itself is never edited. */
	async function updateHighlightNote(highlightId: string, note: string | null): Promise<Highlight> {
		return http.request<Highlight>(`/highlights/${highlightId}`, {
			method: 'PATCH',
			body: { note }
		});
	}

	async function deleteHighlight(highlightId: string): Promise<void> {
		await http.request(`/highlights/${highlightId}`, { method: 'DELETE' });
	}

	return {
		listHighlights,
		listArticleHighlights,
		createHighlight,
		updateHighlightNote,
		deleteHighlight
	};
}

export type HighlightApi = ReturnType<typeof createHighlightApi>;
