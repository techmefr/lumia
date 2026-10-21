import type { Me } from '@lumia/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { articleAudio, resetServerVoice } from './server-voice';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { getMe: vi.fn() }, article: { getArticleAudio: vi.fn() } }
}));

const user = vi.mocked(lumia.user);
const article = vi.mocked(lumia.article);
const configured = { tts_provider: 'openai', tts_api_key_set: true } as Me;

beforeEach(() => {
	vi.clearAllMocks();
	resetServerVoice();
});

describe('articleAudio', () => {
	it('fetches the recording when a provider is configured', async () => {
		const audio = new Blob(['mp3']);
		user.getMe.mockResolvedValue(configured);
		article.getArticleAudio.mockResolvedValue(audio);

		await expect(articleAudio('a-1')()).resolves.toBe(audio);
		expect(article.getArticleAudio).toHaveBeenCalledWith('a-1');
	});

	it('asks nothing of the server when no provider is configured', async () => {
		user.getMe.mockResolvedValue({ tts_provider: null, tts_api_key_set: false } as Me);

		await expect(articleAudio('a-1')()).resolves.toBeNull();
		expect(article.getArticleAudio).not.toHaveBeenCalled();
	});

	it('treats a provider without a key as not configured', async () => {
		user.getMe.mockResolvedValue({ tts_provider: 'openai', tts_api_key_set: false } as Me);

		await expect(articleAudio('a-1')()).resolves.toBeNull();
	});

	it('learns the configuration once, however many articles are read', async () => {
		user.getMe.mockResolvedValue(configured);
		article.getArticleAudio.mockResolvedValue(new Blob(['mp3']));

		await articleAudio('a-1')();
		await articleAudio('a-2')();

		expect(user.getMe).toHaveBeenCalledTimes(1);
	});

	it('asks again after the settings changed', async () => {
		user.getMe.mockResolvedValue(configured);
		article.getArticleAudio.mockResolvedValue(new Blob(['mp3']));
		await articleAudio('a-1')();

		resetServerVoice();
		await articleAudio('a-1')();

		expect(user.getMe).toHaveBeenCalledTimes(2);
	});

	it('answers null when the provider fails, so the browser voice takes over', async () => {
		user.getMe.mockResolvedValue(configured);
		article.getArticleAudio.mockRejectedValue(new Error('502'));

		await expect(articleAudio('a-1')()).resolves.toBeNull();
	});

	it('answers null when the profile cannot be read', async () => {
		user.getMe.mockRejectedValue(new Error('down'));

		await expect(articleAudio('a-1')()).resolves.toBeNull();
	});
});
