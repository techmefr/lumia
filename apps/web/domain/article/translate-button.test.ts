import { ApiError, type ArticleTranslation } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { setLocale } from '$technical/i18n/i18n.svelte';
import TranslateButton from './translate-button.svelte';

// The client is the app's http boundary, so it is what gets replaced.
vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { article: { translateArticle: vi.fn() } }
}));

const api = vi.mocked(lumia.article);

const TRANSLATION: ArticleTranslation = {
	target_lang: 'fr',
	title: 'Bonjour le monde',
	content: 'Le corps de l’article.'
};

type Props = Parameters<typeof TranslateButton>[1];

function widget(translation: ArticleTranslation | null = null) {
	const onchange = vi.fn();
	const { container } = render(TranslateButton, {
		articleId: 'article-1',
		translation,
		onchange
	} as Props);
	const button = () => container.querySelector<HTMLButtonElement>('[data-test-translate-button]')!;
	return {
		onchange,
		button,
		state: () => button().dataset.testTranslateState,
		label: () => button().textContent?.trim().replace(/\s+/g, ' ')
	};
}

beforeEach(() => {
	setLocale('fr');
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
});

describe('asking for a translation', () => {
	it('offers the translation of the article it was given', () => {
		const view = widget();
		expect(view.state()).toBe('original');
		expect(view.label()).toBe('Traduire');
	});

	it('asks for the language the reader is reading the interface in', async () => {
		setLocale('de');
		api.translateArticle.mockResolvedValue(TRANSLATION);

		await fireEvent.click(widget().button());
		await vi.waitFor(() => expect(api.translateArticle).toHaveBeenCalledWith('article-1', 'de'));
	});

	it('hands the translation back to the page', async () => {
		api.translateArticle.mockResolvedValue(TRANSLATION);
		const view = widget();

		await fireEvent.click(view.button());
		await vi.waitFor(() => expect(view.onchange).toHaveBeenCalledWith(TRANSLATION));
	});

	it('says it is working, and refuses a second request while it is', async () => {
		let release: (translation: ArticleTranslation) => void = () => {};
		api.translateArticle.mockReturnValue(
			new Promise<ArticleTranslation>((resolve) => (release = resolve))
		);
		const view = widget();

		await fireEvent.click(view.button());
		await vi.waitFor(() => expect(view.state()).toBe('pending'));
		expect(view.button().disabled).toBe(true);
		expect(view.button().getAttribute('aria-busy')).toBe('true');
		expect(view.label()).toBe('Traduction…');

		release(TRANSLATION);
		await vi.waitFor(() => expect(view.state()).toBe('original'));
	});
});

describe('going back to the original', () => {
	it('offers the original once a translation is on screen', () => {
		const view = widget(TRANSLATION);
		expect(view.state()).toBe('translated');
		expect(view.label()).toBe("Voir l'original");
		expect(view.button().getAttribute('aria-pressed')).toBe('true');
	});

	it('clears the translation instead of asking for another one', async () => {
		const view = widget(TRANSLATION);

		await fireEvent.click(view.button());
		expect(view.onchange).toHaveBeenCalledWith(null);
		expect(api.translateArticle).not.toHaveBeenCalled();
	});
});

describe('when there is nothing to translate with', () => {
	it('tells the reader no provider is configured rather than showing an error', async () => {
		api.translateArticle.mockRejectedValue(new ApiError(503, { detail: 'no_translation_provider' }));
		const view = widget();

		await fireEvent.click(view.button());
		await vi.waitFor(() =>
			expect(toasts.toasts.at(-1)?.message).toBe(
				'Aucun service de traduction configuré pour cette langue.'
			)
		);
		expect(view.onchange).not.toHaveBeenCalled();
	});

	it('reports a provider failure as a failure, keeping the article readable', async () => {
		api.translateArticle.mockRejectedValue(new ApiError(502, { detail: 'translation_failed' }));
		const view = widget();

		await fireEvent.click(view.button());
		await vi.waitFor(() =>
			expect(toasts.toasts.at(-1)?.message).toBe(
				"La traduction a échoué. L'article reste dans sa langue."
			)
		);
	});

	it('goes back to offering a translation after a failure', async () => {
		api.translateArticle.mockRejectedValue(new Error('offline'));
		const view = widget();

		await fireEvent.click(view.button());
		await vi.waitFor(() => expect(view.state()).toBe('original'));
		expect(view.button().disabled).toBe(false);
	});
});
