import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import { highlight } from '../test-support/fixtures';
import HighlightsPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		highlight: {
			listHighlights: vi.fn(),
			updateHighlightNote: vi.fn(),
			deleteHighlight: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia, { deep: true });

function highlightsPage() {
	const { container } = render(HighlightsPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		error: () => q('[role="alert"]'),
		empty: () => q('[data-test-highlights-empty]'),
		cards: () => [...container.querySelectorAll('[data-test-highlight]')],
		card: (id: string) => q(`[data-test-highlight="${id}"]`),
		articleLink: (id: string) =>
			q<HTMLAnchorElement>(`[data-test-highlight="${id}"] [data-test-highlight-article]`),
		edit: (id: string) => q<HTMLButtonElement>(`[data-test-highlight="${id}"] [data-test-highlight-edit]`)!,
		field: () => q<HTMLTextAreaElement>('[data-test-highlight-note-field]')!,
		save: () => q<HTMLButtonElement>('[data-test-highlight-note-save]')!,
		note: (id: string) => q(`[data-test-highlight="${id}"] [data-test-highlight-note]`),
		remove: (id: string) =>
			q<HTMLButtonElement>(`[data-test-highlight="${id}"] [data-test-highlight-delete]`)!
	};
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.highlight.listHighlights.mockResolvedValue([
		highlight('h1', { article_id: 'article-9', article_title: 'Un article' }),
		highlight('h2')
	]);
	api.highlight.updateHighlightNote.mockImplementation(async (id, note) =>
		highlight(id, { note })
	);
	api.highlight.deleteHighlight.mockResolvedValue(undefined);
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('the highlights list', () => {
	it('shows every highlight with a link to its article', async () => {
		const view = highlightsPage();

		await waitFor(() => expect(view.cards()).toHaveLength(2));
		expect(view.articleLink('h1')?.getAttribute('href')).toBe('/articles/article-9');
		expect(view.articleLink('h1')?.textContent).toContain('Un article');
	});

	it('says there is nothing yet when the reader has no highlight', async () => {
		api.highlight.listHighlights.mockResolvedValue([]);
		const view = highlightsPage();

		await waitFor(() => expect(view.empty()).not.toBeNull());
	});

	it('says so when the highlights cannot be fetched', async () => {
		api.highlight.listHighlights.mockRejectedValue(new Error('offline'));
		const view = highlightsPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		highlightsPage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(api.highlight.listHighlights).not.toHaveBeenCalled();
	});
});

describe('changing a highlight', () => {
	it('saves a note and shows it', async () => {
		const view = highlightsPage();
		await waitFor(() => expect(view.cards()).toHaveLength(2));
		await fireEvent.click(view.edit('h1'));
		await fireEvent.input(view.field(), { target: { value: 'A thought' } });

		await fireEvent.click(view.save());

		await waitFor(() => expect(view.note('h1')?.textContent).toContain('A thought'));
		expect(api.highlight.updateHighlightNote).toHaveBeenCalledWith('h1', 'A thought');
	});

	it('keeps the note field open when saving fails', async () => {
		api.highlight.updateHighlightNote.mockRejectedValue(new Error('offline'));
		const view = highlightsPage();
		await waitFor(() => expect(view.cards()).toHaveLength(2));
		await fireEvent.click(view.edit('h1'));
		await fireEvent.input(view.field(), { target: { value: 'A thought' } });

		await fireEvent.click(view.save());

		await waitFor(() => expect(api.highlight.updateHighlightNote).toHaveBeenCalled());
		expect(view.field()).not.toBeNull();
	});

	it('deletes a highlight and drops it from the list', async () => {
		const view = highlightsPage();
		await waitFor(() => expect(view.cards()).toHaveLength(2));

		await fireEvent.click(view.remove('h1'));

		await waitFor(() => expect(view.card('h1')).toBeNull());
		expect(api.highlight.deleteHighlight).toHaveBeenCalledWith('h1');
		expect(view.cards()).toHaveLength(1);
	});

	it('keeps the highlight when deleting fails', async () => {
		api.highlight.deleteHighlight.mockRejectedValue(new Error('offline'));
		const view = highlightsPage();
		await waitFor(() => expect(view.cards()).toHaveLength(2));

		await fireEvent.click(view.remove('h1'));

		await waitFor(() => expect(api.highlight.deleteHighlight).toHaveBeenCalled());
		expect(view.card('h1')).not.toBeNull();
	});
});
