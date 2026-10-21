import type { HttpClient } from '../../technical/http-client';
import type {
	Webhook,
	WebhookCreate,
	WebhookCreated,
	WebhookDelivery,
	WebhookUpdate
} from './types';

export function createWebhookApi(http: HttpClient) {
	async function listWebhooks(): Promise<Webhook[]> {
		return http.request<Webhook[]>('/outbound-webhooks');
	}

	/** The signing secret comes back on this call only: the backend cannot show it again. */
	async function createWebhook(webhook: WebhookCreate): Promise<WebhookCreated> {
		return http.request<WebhookCreated>('/outbound-webhooks', { method: 'POST', body: webhook });
	}

	async function updateWebhook(webhookId: string, update: WebhookUpdate): Promise<Webhook> {
		return http.request<Webhook>(`/outbound-webhooks/${webhookId}`, {
			method: 'PATCH',
			body: update
		});
	}

	async function deleteWebhook(webhookId: string): Promise<void> {
		await http.request<void>(`/outbound-webhooks/${webhookId}`, { method: 'DELETE' });
	}

	async function listDeliveries(webhookId: string): Promise<WebhookDelivery[]> {
		return http.request<WebhookDelivery[]>(`/outbound-webhooks/${webhookId}/deliveries`);
	}

	return { listWebhooks, createWebhook, updateWebhook, deleteWebhook, listDeliveries };
}

export type WebhookApi = ReturnType<typeof createWebhookApi>;
