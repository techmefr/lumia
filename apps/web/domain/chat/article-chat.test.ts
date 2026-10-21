import { ApiError, type ChatMessage } from '@lumia/core';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { setLocale } from '$technical/i18n/i18n.svelte';
import ArticleChat from './article-chat.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { chat: { listChat: vi.fn(), sendChat: vi.fn(), clearChat: vi.fn() } }
}));

const api = vi.mocked(lumia.chat);

function turn(id: string, role: ChatMessage['role'], content: string, action: ChatMessage['action'] = null) {
	return { id, role, content, action, created_at: '2026-10-21T10:00:00Z' } satisfies ChatMessage;
}

type Props = Parameters<typeof ArticleChat>[1];

async function openChat() {
	const { container } = render(ArticleChat, { articleId: 'article-1' } as Props);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	await fireEvent.click(q('[data-test-chat-toggle]')!);
	return {
		q,
		messages: () => [...container.querySelectorAll('[data-test-chat-message]')],
		ask: async (text: string) => {
			await fireEvent.input(q('[data-test-chat-input]')!, { target: { value: text } });
			await fireEvent.submit(q('form')!);
		}
	};
}

beforeEach(() => {
	setLocale('en');
	vi.clearAllMocks();
	api.listChat.mockResolvedValue([]);
});

describe('the article chat', () => {
	it('stays closed and loads nothing until the reader opens it', () => {
		const { container } = render(ArticleChat, { articleId: 'article-1' } as Props);
		expect(container.querySelector('[data-test-chat-toggle]')?.getAttribute('aria-expanded')).toBe('false');
		expect(api.listChat).not.toHaveBeenCalled();
	});

	it('shows the stored thread of the article when opened', async () => {
		api.listChat.mockResolvedValue([turn('1', 'user', 'Why?'), turn('2', 'assistant', 'Because.')]);
		const view = await openChat();
		await waitFor(() => expect(view.messages()).toHaveLength(2));
		expect(api.listChat).toHaveBeenCalledWith('article-1');
	});

	it('announces new messages through a polite live region', async () => {
		const view = await openChat();
		const log = view.q('[data-test-chat-log]')!;
		expect(log.getAttribute('role')).toBe('log');
		expect(log.getAttribute('aria-live')).toBe('polite');
	});

	it('sends a typed question and appends both turns as plain text', async () => {
		api.sendChat.mockResolvedValue([turn('1', 'user', 'Why?'), turn('2', 'assistant', '<img src=x onerror=alert(1)>')]);
		const view = await openChat();

		await view.ask('Why?');

		await waitFor(() => expect(view.messages()).toHaveLength(2));
		expect(api.sendChat).toHaveBeenCalledWith('article-1', { message: 'Why?' });
		expect(view.messages()[1].querySelector('img')).toBeNull();
		expect(view.messages()[1].textContent).toContain('<img src=x onerror=alert(1)>');
	});

	it('sends a quick action and shows its localised label for the reader turn', async () => {
		api.sendChat.mockResolvedValue([
			turn('1', 'user', 'Summarise the article in five sentences at most.', 'summarize'),
			turn('2', 'assistant', 'Short.')
		]);
		const view = await openChat();

		await fireEvent.click(view.q('[data-test-chat-action="summarize"]')!);

		await waitFor(() => expect(view.messages()).toHaveLength(2));
		expect(api.sendChat).toHaveBeenCalledWith('article-1', { action: 'summarize' });
		expect(view.messages()[0].textContent).toContain('Summarise');
		expect(view.messages()[0].textContent).not.toContain('five sentences');
	});

	it('points the reader to the settings when no provider is configured', async () => {
		api.sendChat.mockRejectedValue(new ApiError(503, { detail: 'no_ai_provider' }));
		const view = await openChat();

		await view.ask('Why?');

		await waitFor(() => expect(view.q('[role="alert"]')?.textContent).toContain('settings'));
	});

	it('reports any other failure and keeps the question to retry', async () => {
		api.sendChat.mockRejectedValue(new ApiError(502, { detail: 'chat_failed' }));
		const view = await openChat();

		await view.ask('Why?');

		await waitFor(() => expect(view.q('[role="alert"]')?.textContent).toContain('could not answer'));
		expect(view.q<HTMLTextAreaElement>('[data-test-chat-input]')!.value).toBe('Why?');
	});

	it('does not send an empty question', async () => {
		const view = await openChat();
		expect(view.q<HTMLButtonElement>('[data-test-chat-send]')!.disabled).toBe(true);
	});

	it('clears the conversation', async () => {
		api.listChat.mockResolvedValue([turn('1', 'user', 'Why?'), turn('2', 'assistant', 'Because.')]);
		api.clearChat.mockResolvedValue(undefined);
		const view = await openChat();
		await waitFor(() => expect(view.messages()).toHaveLength(2));

		await fireEvent.click(view.q('[data-test-chat-clear]')!);

		await waitFor(() => expect(view.messages()).toHaveLength(0));
		expect(api.clearChat).toHaveBeenCalledWith('article-1');
	});

	it('reports a thread that could not be loaded', async () => {
		api.listChat.mockRejectedValue(new Error('network'));
		const view = await openChat();
		await waitFor(() => expect(view.q('[role="alert"]')?.textContent).toContain('Could not load'));
	});
});
