import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createChatApi } from './api';

function api(replies: unknown[] = [[]]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, chat: createChatApi(recorder.http) };
}

describe('the chat api', () => {
	it('lists the thread of one article', async () => {
		const { chat, last } = api([[{ id: 'message-1' }]]);
		await expect(chat.listChat('article-1')).resolves.toEqual([{ id: 'message-1' }]);
		expect(last()).toMatchObject({ path: '/articles/article-1/chat', method: 'GET' });
	});

	it('sends a typed question', async () => {
		const { chat, last } = api();
		await chat.sendChat('article-1', { message: 'Why?' });
		expect(last()).toMatchObject({
			path: '/articles/article-1/chat',
			method: 'POST',
			body: { message: 'Why?' }
		});
	});

	it('sends a quick action', async () => {
		const { chat, last } = api();
		await chat.sendChat('article-1', { action: 'summarize' });
		expect(last()).toMatchObject({ method: 'POST', body: { action: 'summarize' } });
	});

	it('clears the thread', async () => {
		const { chat, last } = api([undefined]);
		await chat.clearChat('article-1');
		expect(last()).toMatchObject({ path: '/articles/article-1/chat', method: 'DELETE' });
	});
});
