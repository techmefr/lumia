import type { HttpClient } from '../../technical/http-client';
import type { Tag, TagRef, TagSuggestion } from './types';

export function createTagApi(http: HttpClient) {
	async function listTags(): Promise<Tag[]> {
		return http.request<Tag[]>('/tags');
	}

	async function createTag(name: string): Promise<Tag> {
		return http.request<Tag>('/tags', { method: 'POST', body: { name } });
	}

	async function renameTag(tagId: string, name: string): Promise<Tag> {
		return http.request<Tag>(`/tags/${tagId}`, { method: 'PATCH', body: { name } });
	}

	async function deleteTag(tagId: string): Promise<void> {
		await http.request(`/tags/${tagId}`, { method: 'DELETE' });
	}

	/** Creates the tag on first use, and answers with every tag the article now carries. */
	async function tagArticle(articleId: string, name: string): Promise<TagRef[]> {
		return http.request<TagRef[]>(`/articles/${articleId}/tags`, {
			method: 'POST',
			body: { name }
		});
	}

	async function untagArticle(articleId: string, tagId: string): Promise<TagRef[]> {
		return http.request<TagRef[]>(`/articles/${articleId}/tags/${tagId}`, { method: 'DELETE' });
	}

	/** Free and local: the article's keywords, then the tags the reader uses most. */
	async function getSuggestions(articleId: string): Promise<TagSuggestion[]> {
		return http.request<TagSuggestion[]>(`/articles/${articleId}/tag-suggestions`);
	}

	/** Spends the account's own model, so it only runs when the reader asks. */
	async function getAiSuggestions(articleId: string): Promise<TagSuggestion[]> {
		return http.request<TagSuggestion[]>(`/articles/${articleId}/tag-suggestions/ai`, {
			method: 'POST'
		});
	}

	return {
		listTags,
		createTag,
		renameTag,
		deleteTag,
		tagArticle,
		untagArticle,
		getSuggestions,
		getAiSuggestions
	};
}

export type TagApi = ReturnType<typeof createTagApi>;
