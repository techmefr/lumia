import type { HttpClient } from '../../technical/http-client';
import type { ChatMessage, ChatRequest } from './types';

export function createChatApi(http: HttpClient) {
	async function listChat(articleId: string): Promise<ChatMessage[]> {
		return http.request<ChatMessage[]>(`/articles/${articleId}/chat`);
	}

	/** Resolves with the two turns just stored: the reader's, then the assistant's answer. */
	async function sendChat(articleId: string, request: ChatRequest): Promise<ChatMessage[]> {
		return http.request<ChatMessage[]>(`/articles/${articleId}/chat`, {
			method: 'POST',
			body: request
		});
	}

	async function clearChat(articleId: string): Promise<void> {
		await http.request(`/articles/${articleId}/chat`, { method: 'DELETE' });
	}

	return { listChat, sendChat, clearChat };
}

export type ChatApi = ReturnType<typeof createChatApi>;
