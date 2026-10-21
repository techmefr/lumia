export type WebhookEvent = 'article.saved' | 'article.favorited' | 'playlist.article_added';

export type DeliveryStatus = 'pending' | 'delivered' | 'failed';

export interface Webhook {
	id: string;
	url: string;
	events: WebhookEvent[];
	active: boolean;
	created_at: string;
}

export interface WebhookCreated extends Webhook {
	secret: string;
}

export interface WebhookCreate {
	url: string;
	events: WebhookEvent[];
}

export interface WebhookUpdate {
	url?: string;
	events?: WebhookEvent[];
	active?: boolean;
}

export interface WebhookDelivery {
	id: string;
	event: WebhookEvent;
	status: DeliveryStatus;
	attempts: number;
	last_status_code: number | null;
	last_error: string | null;
	created_at: string;
	delivered_at: string | null;
}

export const WEBHOOK_EVENTS: readonly WebhookEvent[] = [
	'article.saved',
	'article.favorited',
	'playlist.article_added'
];
