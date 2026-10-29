import { ApiError, type Webhook, type WebhookDelivery } from '@lumia/core';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import OutboundWebhooks from './outbound-webhooks.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		webhook: {
			listWebhooks: vi.fn(),
			createWebhook: vi.fn(),
			updateWebhook: vi.fn(),
			deleteWebhook: vi.fn(),
			listDeliveries: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.webhook);

const HOOK: Webhook = {
	id: 'hook-1',
	url: 'https://hooks.example.com/lumia',
	events: ['article.saved'],
	active: true,
	created_at: '2026-10-21T10:00:00Z'
};

function view() {
	const { container } = render(OutboundWebhooks);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	const all = <T extends Element>(selector: string) =>
		Array.from(container.querySelectorAll<T>(selector));
	return {
		url: () => q<HTMLInputElement>('[data-test-webhook-url]')!,
		event: (name: string) => q<HTMLInputElement>(`[data-test-webhook-event="${name}"]`)!,
		form: () => q<HTMLFormElement>('form')!,
		rows: () => all('[data-test-webhook]'),
		secret: () => q<HTMLInputElement>('[data-test-webhook-secret]'),
		error: () => q('[data-test-webhooks-error]'),
		paused: () => q('[data-test-webhook-paused]'),
		toggle: () => q<HTMLButtonElement>('[data-test-webhook-toggle]')!,
		remove: () => q<HTMLButtonElement>('[data-test-webhook-remove]')!,
		history: () => q<HTMLButtonElement>('[data-test-webhook-history]')!,
		deliveries: () => all('[data-test-delivery]'),
		noDeliveries: () => q('[data-test-deliveries-empty]'),
		empty: () => q('[data-test-webhooks-empty]')
	};
}

async function submit(page: ReturnType<typeof view>, url: string) {
	await fireEvent.input(page.url(), { target: { value: url } });
	await fireEvent.submit(page.form());
}

beforeEach(() => {
	for (const mock of Object.values(api)) mock.mockReset();
	api.listWebhooks.mockResolvedValue([]);
});

afterEach(cleanup);

describe('the outgoing webhooks card', () => {
	it('says there is none when the reader has no webhook', async () => {
		const page = view();

		await waitFor(() => expect(page.empty()).not.toBeNull());
		expect(page.rows()).toHaveLength(0);
	});

	it('lists the webhooks the reader already has', async () => {
		api.listWebhooks.mockResolvedValue([HOOK]);
		const page = view();

		await waitFor(() => expect(page.rows()).toHaveLength(1));
		expect(page.rows()[0].textContent).toContain('https://hooks.example.com/lumia');
		expect(page.secret()).toBeNull();
	});

	it('sends the address and the ticked events, then shows the secret once', async () => {
		api.createWebhook.mockResolvedValue({ ...HOOK, secret: 'the-secret' });
		const page = view();
		await fireEvent.click(page.event('article.favorited'));

		await submit(page, ' https://hooks.example.com/lumia ');

		await waitFor(() => expect(page.secret()).not.toBeNull());
		expect(api.createWebhook).toHaveBeenCalledWith({
			url: 'https://hooks.example.com/lumia',
			events: ['article.saved', 'article.favorited']
		});
		expect(page.secret()!.value).toBe('the-secret');
		expect(page.rows()).toHaveLength(1);
		expect(page.url().value).toBe('');
	});

	it('refuses to send a webhook that listens to nothing', async () => {
		const page = view();
		await fireEvent.click(page.event('article.saved'));

		await submit(page, 'https://hooks.example.com/lumia');

		await waitFor(() => expect(page.error()).not.toBeNull());
		expect(api.createWebhook).not.toHaveBeenCalled();
	});

	it('reports an address the backend guard refused', async () => {
		api.createWebhook.mockRejectedValue(new ApiError(422, { detail: 'webhook_url_blocked' }));
		const page = view();

		await submit(page, 'https://10.0.0.1/x');

		await waitFor(() => expect(page.error()).not.toBeNull());
		expect(page.error()!.textContent).toMatch(/public|publique/i);
		expect(page.secret()).toBeNull();
	});

	it('reports that the limit of webhooks is reached', async () => {
		api.createWebhook.mockRejectedValue(new ApiError(409, { detail: 'webhook_limit_reached' }));
		const page = view();

		await submit(page, 'https://hooks.example.com/lumia');

		await waitFor(() => expect(page.error()).not.toBeNull());
		expect(page.error()!.textContent).toMatch(/maxim/i);
	});

	it('pauses a webhook and says so', async () => {
		api.listWebhooks.mockResolvedValue([HOOK]);
		api.updateWebhook.mockResolvedValue({ ...HOOK, active: false });
		const page = view();
		await waitFor(() => expect(page.rows()).toHaveLength(1));

		await fireEvent.click(page.toggle());

		await waitFor(() => expect(page.paused()).not.toBeNull());
		expect(api.updateWebhook).toHaveBeenCalledWith('hook-1', { active: false });
	});

	it('removes a webhook', async () => {
		api.listWebhooks.mockResolvedValue([HOOK]);
		api.deleteWebhook.mockResolvedValue(undefined);
		const page = view();
		await waitFor(() => expect(page.rows()).toHaveLength(1));

		await fireEvent.click(page.remove());

		await waitFor(() => expect(page.rows()).toHaveLength(0));
		expect(api.deleteWebhook).toHaveBeenCalledWith('hook-1');
	});

	it('opens the delivery history with its outcome and last error, then closes it', async () => {
		const delivery: WebhookDelivery = {
			id: 'delivery-1',
			event: 'article.saved',
			status: 'failed',
			attempts: 5,
			last_status_code: 503,
			last_error: 'HTTP 503',
			created_at: '2026-10-21T10:00:00Z',
			delivered_at: null
		};
		api.listWebhooks.mockResolvedValue([HOOK]);
		api.listDeliveries.mockResolvedValue([delivery]);
		const page = view();
		await waitFor(() => expect(page.rows()).toHaveLength(1));

		await fireEvent.click(page.history());

		await waitFor(() => expect(page.deliveries()).toHaveLength(1));
		expect((page.deliveries()[0] as HTMLElement).dataset.testDelivery).toBe('failed');
		expect(page.deliveries()[0].textContent).toContain('HTTP 503');
		expect(page.history().getAttribute('aria-expanded')).toBe('true');

		await fireEvent.click(page.history());

		expect(page.deliveries()).toHaveLength(0);
		expect(page.history().getAttribute('aria-expanded')).toBe('false');
	});

	it('says when a webhook has had no delivery yet', async () => {
		api.listWebhooks.mockResolvedValue([HOOK]);
		api.listDeliveries.mockResolvedValue([]);
		const page = view();
		await waitFor(() => expect(page.rows()).toHaveLength(1));

		await fireEvent.click(page.history());

		await waitFor(() => expect(page.noDeliveries()).not.toBeNull());
	});

	it('reports a list that could not be loaded', async () => {
		api.listWebhooks.mockRejectedValue(new Error('down'));
		const page = view();

		await waitFor(() => expect(page.error()).not.toBeNull());
	});
});
