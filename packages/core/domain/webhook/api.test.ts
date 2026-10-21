import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createWebhookApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, webhooks: createWebhookApi(recorder.http) };
}

describe('outbound webhooks', () => {
	it('lists them with the session', async () => {
		const { webhooks, last } = api([[{ id: 'hook-1' }]]);
		await expect(webhooks.listWebhooks()).resolves.toEqual([{ id: 'hook-1' }]);
		expect(last()).toMatchObject({ path: '/outbound-webhooks', method: 'GET', auth: true });
	});

	it('creates one from an address and the events it listens to', async () => {
		const { webhooks, last } = api([{ id: 'hook-1', secret: 'shh' }]);
		await expect(
			webhooks.createWebhook({ url: 'https://hooks.example.com/x', events: ['article.saved'] })
		).resolves.toMatchObject({ secret: 'shh' });
		expect(last()).toMatchObject({
			path: '/outbound-webhooks',
			method: 'POST',
			body: { url: 'https://hooks.example.com/x', events: ['article.saved'] }
		});
	});

	it('pauses one with a PATCH', async () => {
		const { webhooks, last } = api([{ id: 'hook-1' }]);
		await webhooks.updateWebhook('hook-1', { active: false });
		expect(last()).toMatchObject({
			path: '/outbound-webhooks/hook-1',
			method: 'PATCH',
			body: { active: false }
		});
	});

	it('removes one with a DELETE', async () => {
		const { webhooks, last } = api([undefined]);
		await webhooks.deleteWebhook('hook-1');
		expect(last()).toMatchObject({ path: '/outbound-webhooks/hook-1', method: 'DELETE' });
	});

	it('reads the delivery history of one', async () => {
		const { webhooks, last } = api([[{ id: 'delivery-1' }]]);
		await expect(webhooks.listDeliveries('hook-1')).resolves.toEqual([{ id: 'delivery-1' }]);
		expect(last()).toMatchObject({ path: '/outbound-webhooks/hook-1/deliveries', method: 'GET' });
	});
});
