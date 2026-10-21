import type { HttpClient } from '../../technical/http-client';
import type { NewsletterInboxCreated, NewsletterInboxStatus } from './types';

export function createNewsletterApi(http: HttpClient) {
	async function getInboxStatus(): Promise<NewsletterInboxStatus> {
		return http.request<NewsletterInboxStatus>('/newsletters/inbox');
	}

	/** Issues a new address, which retires the previous one. The token is shown only here. */
	async function createInbox(): Promise<NewsletterInboxCreated> {
		return http.request<NewsletterInboxCreated>('/newsletters/inbox', {
			method: 'POST'
		});
	}

	async function revokeInbox(): Promise<void> {
		await http.request<void>('/newsletters/inbox', { method: 'DELETE' });
	}

	return { getInboxStatus, createInbox, revokeInbox };
}

export type NewsletterApi = ReturnType<typeof createNewsletterApi>;
