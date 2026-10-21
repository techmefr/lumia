import type { Me } from '@lumia/core';
import { fireEvent, render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import TtsSettings from './tts-settings.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { getMe: vi.fn(), updateMe: vi.fn() }, article: { getArticleAudio: vi.fn() } }
}));

const api = vi.mocked(lumia.user);

function me(overrides: Partial<Me> = {}): Me {
	return {
		id: 'user-1',
		tts_provider: null,
		tts_endpoint_url: null,
		tts_model: null,
		tts_voice: null,
		tts_api_key_set: false,
		...overrides
	} as Me;
}

async function loaded(account: Me = me()) {
	api.getMe.mockResolvedValue(account);
	const { container } = render(TtsSettings);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	await vi.waitFor(() => expect(q('[data-test-tts-loading]')).toBeNull());
	return {
		unavailable: () => q('[data-test-tts-unavailable]'),
		error: () => q('[data-test-tts-error]'),
		provider: () => q<HTMLSelectElement>('[data-test-tts-provider]')!,
		key: () => q<HTMLInputElement>('[data-test-tts-key]'),
		model: () => q<HTMLInputElement>('[data-test-tts-model]'),
		voice: () => q<HTMLInputElement>('[data-test-tts-voice]'),
		endpoint: () => q<HTMLInputElement>('[data-test-tts-endpoint]'),
		deleteKey: () => q<HTMLButtonElement>('[data-test-delete-tts-key]'),
		save: () => q<HTMLButtonElement>('[data-test-tts-save]')!
	};
}

beforeEach(() => {
	vi.clearAllMocks();
	api.updateMe.mockImplementation(async (payload) => me(payload as Partial<Me>));
});

describe('the natural voice settings', () => {
	it('says so when the settings cannot be loaded', async () => {
		api.getMe.mockRejectedValue(new Error('down'));
		const { container } = render(TtsSettings);
		await vi.waitFor(() =>
			expect(container.querySelector('[data-test-tts-unavailable]')).not.toBeNull()
		);
	});

	it('shows no field until a provider is chosen', async () => {
		const view = await loaded();
		expect(view.key()).toBeNull();
		expect(view.model()).toBeNull();
	});

	it('shows the endpoint only for a self-hosted server', async () => {
		const view = await loaded();
		await fireEvent.change(view.provider(), { target: { value: 'openai' } });
		expect(view.endpoint()).toBeNull();
		await fireEvent.change(view.provider(), { target: { value: 'custom' } });
		expect(view.endpoint()).not.toBeNull();
	});

	it('sends the provider, voice and key when saved', async () => {
		const view = await loaded();
		await fireEvent.change(view.provider(), { target: { value: 'custom' } });
		await fireEvent.input(view.key()!, { target: { value: ' tts-secret ' } });
		await fireEvent.input(view.model()!, { target: { value: 'kokoro' } });
		await fireEvent.input(view.voice()!, { target: { value: 'af_bella' } });
		await fireEvent.input(view.endpoint()!, { target: { value: 'https://voice.test/v1' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() =>
			expect(api.updateMe).toHaveBeenCalledWith({
				tts_provider: 'custom',
				tts_model: 'kokoro',
				tts_voice: 'af_bella',
				tts_endpoint_url: 'https://voice.test/v1',
				tts_api_key: 'tts-secret'
			})
		);
	});

	it('leaves the key out when the field is blank, so the stored one is kept', async () => {
		const view = await loaded(me({ tts_provider: 'openai', tts_api_key_set: true }));
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalled());
		expect(api.updateMe.mock.calls[0][0]).not.toHaveProperty('tts_api_key');
	});

	it('turns the voice off by choosing no provider', async () => {
		const view = await loaded(me({ tts_provider: 'openai', tts_api_key_set: true }));
		await fireEvent.change(view.provider(), { target: { value: '' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() =>
			expect(api.updateMe).toHaveBeenCalledWith(expect.objectContaining({ tts_provider: null }))
		);
	});

	it('deletes the stored key on request', async () => {
		const view = await loaded(me({ tts_provider: 'openai', tts_api_key_set: true }));
		await fireEvent.click(view.deleteKey()!);

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalledWith({ tts_api_key: null }));
	});

	it('reports a failed save', async () => {
		const view = await loaded();
		api.updateMe.mockRejectedValue(new Error('refused'));
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
	});
});
