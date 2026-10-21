import { ApiError, type Tag, type TagRef, type TagSuggestion } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import ArticleTags from './article-tags.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		tag: {
			listTags: vi.fn(),
			getSuggestions: vi.fn(),
			tagArticle: vi.fn(),
			untagArticle: vi.fn(),
			getAiSuggestions: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.tag);

const CUISINE: TagRef = { id: 't1', name: 'Cuisine' };
const KNOWN: Tag[] = [
	{ id: 't1', name: 'Cuisine', article_count: 3 },
	{ id: 't2', name: 'Voyage', article_count: 1 }
];
const SUGGESTIONS: TagSuggestion[] = [
	{ name: 'recette', source: 'keyword' },
	{ name: 'Voyage', source: 'used' }
];

type Props = Parameters<typeof ArticleTags>[1];

function editor(tags: TagRef[] = []) {
	const onchange = vi.fn();
	const { container } = render(ArticleTags, { articleId: 'article-1', tags, onchange } as Props);
	const all = <T extends Element>(selector: string) => [
		...container.querySelectorAll<T>(selector)
	];
	return {
		onchange,
		input: () => container.querySelector<HTMLInputElement>('[data-test-tag-input]')!,
		submit: () => container.querySelector<HTMLButtonElement>('[data-test-tag-submit]')!,
		ai: () => container.querySelector<HTMLButtonElement>('[data-test-tag-ai]')!,
		chips: () => all<HTMLElement>('[data-test-tag]').map((node) => node.dataset.testTag),
		suggestions: () =>
			all<HTMLElement>('[data-test-suggestion]').map((node) => ({
				name: node.dataset.testSuggestion,
				source: node.dataset.testSuggestionSource
			})),
		options: () => all<HTMLOptionElement>('datalist option').map((option) => option.value),
		click: (selector: string, index = 0) =>
			fireEvent.click(all<HTMLElement>(selector)[index]),
		type: (value: string) => fireEvent.input(container.querySelector('[data-test-tag-input]')!, { target: { value } }),
		form: () => container.querySelector('form')!
	};
}

async function loaded(tags: TagRef[] = []) {
	const view = editor(tags);
	await vi.waitFor(() => expect(api.getSuggestions).toHaveBeenCalledWith('article-1'));
	await vi.waitFor(() => expect(view.options()).toHaveLength(KNOWN.length));
	return view;
}

beforeEach(() => {
	api.listTags.mockResolvedValue(KNOWN);
	api.getSuggestions.mockResolvedValue(SUGGESTIONS);
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.resetAllMocks();
});

describe('what it shows', () => {
	it('lists the article tags as links to the filtered list', async () => {
		const view = await loaded([CUISINE]);
		expect(view.chips()).toEqual(['t1']);
		const link = document.querySelector<HTMLAnchorElement>('[data-test-tag-link]')!;
		expect(link.getAttribute('href')).toContain('tag_id=t1&tag_name=Cuisine');
	});

	it('offers the reader existing tags for autocompletion', async () => {
		const view = await loaded();
		expect(view.options()).toEqual(['Cuisine', 'Voyage']);
	});

	it('shows the suggestions with where they come from', async () => {
		const view = await loaded();
		await vi.waitFor(() =>
			expect(view.suggestions()).toEqual([
				{ name: 'recette', source: 'keyword' },
				{ name: 'Voyage', source: 'used' }
			])
		);
	});

	it('hides a suggestion the article already carries, whatever its case', async () => {
		api.getSuggestions.mockResolvedValue([{ name: 'cuisine', source: 'used' }, ...SUGGESTIONS]);
		const view = await loaded([CUISINE]);
		await vi.waitFor(() => expect(view.suggestions()).toHaveLength(2));
	});

	it('still works when the suggestions cannot be loaded', async () => {
		api.getSuggestions.mockRejectedValue(new Error('down'));
		const view = editor([CUISINE]);
		await vi.waitFor(() => expect(api.getSuggestions).toHaveBeenCalled());
		expect(view.chips()).toEqual(['t1']);
		expect(view.suggestions()).toEqual([]);
	});
});

describe('tagging', () => {
	it('adds the typed name and reports the article tags it now carries', async () => {
		api.tagArticle.mockResolvedValue([CUISINE]);
		const view = await loaded();
		await view.type('  Cuisine  ');
		await fireEvent.submit(view.form());
		await vi.waitFor(() => expect(view.onchange).toHaveBeenCalledWith([CUISINE]));
		expect(api.tagArticle).toHaveBeenCalledWith('article-1', 'Cuisine');
		expect(view.input().value).toBe('');
	});

	it('keeps the add button off while the field is blank', async () => {
		const view = await loaded();
		expect(view.submit().disabled).toBe(true);
		await view.type('x');
		expect(view.submit().disabled).toBe(false);
	});

	it('accepts a suggestion with one click', async () => {
		api.tagArticle.mockResolvedValue([{ id: 't9', name: 'recette' }]);
		const view = await loaded();
		await vi.waitFor(() => expect(view.suggestions()).toHaveLength(2));
		await view.click('[data-test-suggestion-accept]');
		await vi.waitFor(() => expect(api.tagArticle).toHaveBeenCalledWith('article-1', 'recette'));
	});

	it('writes nothing until the reader accepts: dismissing a suggestion only hides it', async () => {
		const view = await loaded();
		await vi.waitFor(() => expect(view.suggestions()).toHaveLength(2));
		await view.click('[data-test-suggestion-dismiss]');
		await vi.waitFor(() => expect(view.suggestions()).toHaveLength(1));
		expect(api.tagArticle).not.toHaveBeenCalled();
	});

	it('removes a tag and reports what is left', async () => {
		api.untagArticle.mockResolvedValue([]);
		const view = await loaded([CUISINE]);
		await view.click('[data-test-tag-remove]');
		await vi.waitFor(() => expect(api.untagArticle).toHaveBeenCalledWith('article-1', 't1'));
		await vi.waitFor(() => expect(view.onchange).toHaveBeenCalledWith([]));
	});

	it('says so when adding fails', async () => {
		api.tagArticle.mockRejectedValue(new Error('down'));
		const view = await loaded();
		await view.type('x');
		await fireEvent.submit(view.form());
		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(view.onchange).not.toHaveBeenCalled();
	});

	it('says so when removing fails', async () => {
		api.untagArticle.mockRejectedValue(new Error('down'));
		const view = await loaded([CUISINE]);
		await view.click('[data-test-tag-remove]');
		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
	});
});

describe('the model suggestions', () => {
	it('adds what the model proposes next to the local ones, skipping duplicates', async () => {
		api.getAiSuggestions.mockResolvedValue([
			{ name: 'recette', source: 'ai' },
			{ name: 'Gastronomie', source: 'ai' }
		]);
		const view = await loaded();
		await vi.waitFor(() => expect(view.suggestions()).toHaveLength(2));
		await fireEvent.click(view.ai());
		await vi.waitFor(() => expect(view.suggestions()).toHaveLength(3));
		expect(view.suggestions().at(-1)).toEqual({ name: 'Gastronomie', source: 'ai' });
	});

	it('says when the model has nothing new', async () => {
		api.getAiSuggestions.mockResolvedValue([]);
		const view = await loaded();
		await fireEvent.click(view.ai());
		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
	});

	it('tells the reader there is no provider on a 503', async () => {
		api.getAiSuggestions.mockRejectedValue(new ApiError(503, { detail: 'no_ai_provider' }));
		const view = await loaded();
		await fireEvent.click(view.ai());
		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].message).toBe('No AI provider is set up on this account.');
	});

	it('reports any other failure as a failure', async () => {
		api.getAiSuggestions.mockRejectedValue(new ApiError(502, { detail: 'ai_suggestion_failed' }));
		const view = await loaded();
		await fireEvent.click(view.ai());
		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].message).toBe('The suggestions could not be fetched.');
	});
});
