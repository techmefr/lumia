import type { Me } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import AiSettings from './ai-settings.svelte';

// The client is the app's http boundary, so it is what gets replaced.
vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { getMe: vi.fn(), updateMe: vi.fn() } }
}));

const api = vi.mocked(lumia.user);

function me(overrides: Partial<Me> = {}): Me {
	return {
		id: 'user-1',
		email: 'lecteur@example.test',
		role: 'user',
		preferred_language: 'fr',
		ai_provider: null,
		ai_model: null,
		ai_endpoint_url: null,
		ai_api_key_set: false,
		translation_provider: null,
		translation_api_key_set: false,
		...overrides
	} as Me;
}

function panel() {
	const { container } = render(AiSettings);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loading: () => q('[data-test-ai-loading]'),
		unavailable: () => q('[data-test-ai-unavailable]'),
		error: () => q('[data-test-ai-error]'),
		language: () => q<HTMLSelectElement>('[data-test-reading-language]')!,
		untranslatable: () => q('[data-test-language-untranslatable]'),
		provider: () => q<HTMLSelectElement>('[data-test-ai-provider]')!,
		key: () => q<HTMLInputElement>('[data-test-ai-key]'),
		model: () => q<HTMLInputElement>('[data-test-ai-model]'),
		endpoint: () => q<HTMLInputElement>('[data-test-ai-endpoint]'),
		deleteKey: () => q<HTMLButtonElement>('[data-test-delete-ai-key]'),
		translationProvider: () => q<HTMLSelectElement>('[data-test-translation-provider]')!,
		translationKey: () => q<HTMLInputElement>('[data-test-translation-key]'),
		deleteTranslationKey: () => q<HTMLButtonElement>('[data-test-delete-translation-key]'),
		save: () => q<HTMLButtonElement>('[data-test-ai-save]')!
	};
}

async function loaded(account: Me = me()) {
	api.getMe.mockResolvedValue(account);
	const view = panel();
	await vi.waitFor(() => expect(view.loading()).toBeNull());
	return view;
}

beforeEach(() => {
	api.getMe.mockReset();
	api.updateMe.mockReset();
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.clearAllMocks();
});

describe('loading the account', () => {
	it('announces the wait', () => {
		api.getMe.mockReturnValue(new Promise(() => {}));
		const view = panel();

		expect(view.loading()?.getAttribute('aria-live')).toBe('polite');
	});

	it('shows what the account has set', async () => {
		const view = await loaded(
			me({ preferred_language: 'en', ai_provider: 'mistral', ai_model: 'mistral-small' })
		);

		expect(view.language().value).toBe('en');
		expect(view.provider().value).toBe('mistral');
		expect(view.model()?.value).toBe('mistral-small');
	});

	it('says so and shows no form when the account could not be read', async () => {
		api.getMe.mockRejectedValue(new Error('offline'));
		const view = panel();

		await vi.waitFor(() => expect(view.unavailable()).not.toBeNull());
		expect(view.provider()).toBeNull();
	});
});

describe('the reading language', () => {
	it('offers the ten interface languages', async () => {
		const view = await loaded();

		expect(view.language().options).toHaveLength(10);
	});

	// Named in their own language, because someone who has landed on the wrong one has to be able
	// to find their way back out.
	it('names each language in itself', async () => {
		const view = await loaded();

		const labels = [...view.language().options].map((option) => option.textContent?.trim());
		expect(labels).toContain('Français');
		expect(labels).toContain('English');
	});

	// Said at the moment of the choice rather than discovered later by wondering why nothing is
	// translated: no provider covers malagasy, so those articles stay in their own language.
	it('warns when the chosen language has no translation provider', async () => {
		const view = await loaded();

		await fireEvent.change(view.language(), { target: { value: 'mg' } });

		await vi.waitFor(() => expect(view.untranslatable()).not.toBeNull());
	});

	it('says nothing for a language that is covered', async () => {
		const view = await loaded();

		await fireEvent.change(view.language(), { target: { value: 'en' } });

		expect(view.untranslatable()).toBeNull();
	});
});

describe('choosing an ai provider', () => {
	it('offers none, the four hosted ones, and a custom endpoint', async () => {
		const view = await loaded();

		expect([...view.provider().options].map((option) => option.value)).toEqual([
			'',
			'mistral',
			'openai',
			'anthropic',
			'gemma',
			'custom'
		]);
	});

	// Without a provider there is nothing to configure: a key field for a provider nobody chose is
	// an invitation to paste a secret that goes nowhere.
	it('asks for no key while there is no provider', async () => {
		const view = await loaded();

		expect(view.key()).toBeNull();
		expect(view.model()).toBeNull();
	});

	it('asks for a key and a model once a provider is chosen', async () => {
		const view = await loaded();

		await fireEvent.change(view.provider(), { target: { value: 'openai' } });

		await vi.waitFor(() => expect(view.key()).not.toBeNull());
		expect(view.model()).not.toBeNull();
	});

	// The endpoint cannot be guessed for a self-hosted model, and is meaningless for a hosted one.
	it('asks for an endpoint only for a custom provider', async () => {
		const view = await loaded();

		await fireEvent.change(view.provider(), { target: { value: 'openai' } });
		await vi.waitFor(() => expect(view.key()).not.toBeNull());
		expect(view.endpoint()).toBeNull();

		await fireEvent.change(view.provider(), { target: { value: 'custom' } });

		await vi.waitFor(() => expect(view.endpoint()).not.toBeNull());
	});
});

describe('how the keys are handled', () => {
	// The api never returns a key, so the field is always empty on arrival. Prefilling it with
	// anything, even dots, would mean a save re-sends that placeholder as the new key.
	it('never prefills the key field, even when one is on file', async () => {
		const view = await loaded(me({ ai_provider: 'openai', ai_api_key_set: true }));

		expect(view.key()?.value).toBe('');
	});

	it('says a key is already on file, and says so in the placeholder too', async () => {
		const view = await loaded(me({ ai_provider: 'openai', ai_api_key_set: true }));

		expect(view.container.querySelector('label[for="ai-key"]')?.textContent).toMatch(/\S/);
		expect(view.key()?.placeholder).not.toBe('sk-…');
	});

	it('keeps the key out of sight while it is typed', async () => {
		const view = await loaded(me({ ai_provider: 'openai' }));

		expect(view.key()?.type).toBe('password');
		expect(view.key()?.getAttribute('autocomplete')).toBe('off');
	});

	// An empty string means "remove the key" server side, so leaving the field blank has to omit
	// the field entirely. Sending it empty would wipe a working key on every unrelated save.
	it('leaves a stored key alone when the field is left blank', async () => {
		api.updateMe.mockResolvedValue(me({ ai_provider: 'openai', ai_api_key_set: true }));
		const view = await loaded(me({ ai_provider: 'openai', ai_api_key_set: true }));

		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalled());
		expect(api.updateMe.mock.calls[0][0]).not.toHaveProperty('ai_api_key');
	});

	it('sends the key when one was typed', async () => {
		api.updateMe.mockResolvedValue(me({ ai_provider: 'openai', ai_api_key_set: true }));
		const view = await loaded(me({ ai_provider: 'openai' }));

		await fireEvent.input(view.key()!, { target: { value: '  sk-abc  ' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalled());
		expect(api.updateMe.mock.calls[0][0]).toMatchObject({ ai_api_key: 'sk-abc' });
	});

	it('treats a field of spaces as blank', async () => {
		api.updateMe.mockResolvedValue(me({ ai_provider: 'openai' }));
		const view = await loaded(me({ ai_provider: 'openai' }));

		await fireEvent.input(view.key()!, { target: { value: '   ' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalled());
		expect(api.updateMe.mock.calls[0][0]).not.toHaveProperty('ai_api_key');
	});

	it('offers to delete a key only when there is one', async () => {
		const withKey = await loaded(me({ ai_provider: 'openai', ai_api_key_set: true }));
		expect(withKey.deleteKey()).not.toBeNull();

		const without = await loaded(me({ ai_provider: 'openai' }));
		expect(without.deleteKey()).toBeNull();
	});

	it('deletes the key by sending an explicit null', async () => {
		api.updateMe.mockResolvedValue(me({ ai_provider: 'openai' }));
		const view = await loaded(me({ ai_provider: 'openai', ai_api_key_set: true }));

		await fireEvent.click(view.deleteKey()!);

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalledWith({ ai_api_key: null }));
	});

	it('deletes the translation key the same way', async () => {
		api.updateMe.mockResolvedValue(me({ translation_provider: 'deepl' }));
		const view = await loaded(me({ translation_provider: 'deepl', translation_api_key_set: true }));

		await fireEvent.click(view.deleteTranslationKey()!);

		await vi.waitFor(() =>
			expect(api.updateMe).toHaveBeenCalledWith({ translation_api_key: null })
		);
	});

	// Every other string on this screen goes through the catalogue; this placeholder used to be a
	// french sentence hardcoded in a screen that exists in ten languages.
	it('translates the placeholder that says a translation key is on file', async () => {
		const view = await loaded(me({ translation_provider: 'deepl', translation_api_key_set: true }));

		expect(view.translationKey()?.placeholder).not.toContain('Laisser vide');
	});
});

describe('the translation provider', () => {
	it('offers none or DeepL', async () => {
		const view = await loaded();

		expect([...view.translationProvider().options].map((option) => option.value)).toEqual([
			'',
			'deepl'
		]);
	});

	it('asks for no key while there is no provider', async () => {
		const view = await loaded();

		expect(view.translationKey()).toBeNull();
	});

	it('asks for a key once DeepL is chosen', async () => {
		const view = await loaded();

		await fireEvent.change(view.translationProvider(), { target: { value: 'deepl' } });

		await vi.waitFor(() => expect(view.translationKey()).not.toBeNull());
	});
});

describe('saving', () => {
	it('sends everything that was chosen', async () => {
		api.updateMe.mockResolvedValue(me({ preferred_language: 'en', ai_provider: 'custom' }));
		const view = await loaded();

		await fireEvent.change(view.language(), { target: { value: 'en' } });
		await fireEvent.change(view.provider(), { target: { value: 'custom' } });
		await vi.waitFor(() => expect(view.endpoint()).not.toBeNull());
		await fireEvent.input(view.model()!, { target: { value: 'voxtral-small' } });
		await fireEvent.input(view.endpoint()!, { target: { value: 'http://voxtral.local/v1' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalled());
		expect(api.updateMe.mock.calls[0][0]).toMatchObject({
			preferred_language: 'en',
			ai_provider: 'custom',
			ai_model: 'voxtral-small',
			ai_endpoint_url: 'http://voxtral.local/v1'
		});
	});

	// Choosing "none" has to clear the provider server side, not leave the previous one in place.
	it('clears a provider that was set back to none', async () => {
		api.updateMe.mockResolvedValue(me());
		const view = await loaded(me({ ai_provider: 'openai', ai_model: 'gpt-4o' }));

		await fireEvent.change(view.provider(), { target: { value: '' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalled());
		expect(api.updateMe.mock.calls[0][0]).toMatchObject({ ai_provider: null });
	});

	it('clears an emptied model rather than sending an empty string', async () => {
		api.updateMe.mockResolvedValue(me({ ai_provider: 'openai' }));
		const view = await loaded(me({ ai_provider: 'openai', ai_model: 'gpt-4o' }));

		await fireEvent.input(view.model()!, { target: { value: '  ' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(api.updateMe).toHaveBeenCalled());
		expect(api.updateMe.mock.calls[0][0]).toMatchObject({ ai_model: null });
	});

	it('confirms the save', async () => {
		api.updateMe.mockResolvedValue(me());
		const view = await loaded();

		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
	});

	it('shows what came back, so the key-on-file marker is up to date', async () => {
		api.updateMe.mockResolvedValue(me({ ai_provider: 'openai', ai_api_key_set: true }));
		const view = await loaded(me({ ai_provider: 'openai' }));

		await fireEvent.input(view.key()!, { target: { value: 'sk-abc' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(view.deleteKey()).not.toBeNull());
	});

	// The field is cleared on the way back precisely because the key is now on file: leaving it
	// filled would re-send it on the next unrelated save.
	it('clears the key field once the key is stored', async () => {
		api.updateMe.mockResolvedValue(me({ ai_provider: 'openai', ai_api_key_set: true }));
		const view = await loaded(me({ ai_provider: 'openai' }));

		await fireEvent.input(view.key()!, { target: { value: 'sk-abc' } });
		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(view.key()?.value).toBe(''));
	});

	it('says so when the save failed', async () => {
		api.updateMe.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('lets the save be tried again after a failure', async () => {
		api.updateMe.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(view.save().disabled).toBe(false));
	});

	it('disables the button while it saves, so it cannot be pressed twice', async () => {
		api.updateMe.mockReturnValue(new Promise(() => {}));
		const view = await loaded();

		await fireEvent.click(view.save());

		await vi.waitFor(() => expect(view.save().disabled).toBe(true));
	});
});
