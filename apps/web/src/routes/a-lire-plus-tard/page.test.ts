import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import { articleDetail, articleSummary } from '../test-support/fixtures';
import ReadLaterPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		article: { saveUrl: vi.fn() },
		recommendation: { getSaved: vi.fn(), sendFeedback: vi.fn() }
	}
}));

// The real runtime opens IndexedDB at module scope, which jsdom does not provide. The in-memory
// database already backs OfflineLibrary's own unit tests, so reusing it here exercises the real
// class instead of a hand-rolled stub that would drift from its actual interface. Imported inside
// the factory, not at the top of the file: vi.mock is hoisted above ordinary imports, so a
// top-level binding would still be undefined when this factory runs.
vi.mock('$technical/offline/offline-runtime', async () => {
	const { OfflineLibrary } = await import('$domain/offline/offline-library.svelte');
	const { OfflineWriteQueue } = await import('$domain/offline/offline-write-queue.svelte');
	const { createInMemoryOfflineDatabase } = await import(
		'$technical/offline/in-memory-offline-database'
	);
	const db = createInMemoryOfflineDatabase();
	return {
		offlineLibrary: new OfflineLibrary(db),
		writeQueue: new OfflineWriteQueue(db)
	};
});

const api = vi.mocked(lumia, { deep: true });

const PAGE_SIZE = 24;

function readLaterPage() {
	const { container } = render(ReadLaterPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		listError: () => q('[data-test-list-error]'),
		saveError: () => q('[data-test-save-error]'),
		saveForm: () => q<HTMLFormElement>('[data-test-save-url-form]')!,
		url: () => q<HTMLInputElement>('#save-url')!,
		cards: () => [...container.querySelectorAll('[data-test-article-card]')],
		card: (id: string) => q(`[data-test-article-card="${id}"]`),
		browse: () => q<HTMLAnchorElement>('a[href$="/articles"]'),
		loadMore: () => q<HTMLButtonElement>('[data-test-load-more]')
	};
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.recommendation.getSaved.mockResolvedValue([articleSummary('saved-1')]);
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('the read-later list', () => {
	it('shows what the reader put aside', async () => {
		const view = readLaterPage();

		await waitFor(() => expect(view.card('saved-1')).not.toBeNull());
		expect(api.recommendation.getSaved).toHaveBeenCalledWith(PAGE_SIZE, 0);
	});

	it('points an empty list back at the article list', async () => {
		api.recommendation.getSaved.mockResolvedValue([]);
		const view = readLaterPage();

		await waitFor(() => expect(view.browse()).not.toBeNull());
	});

	it('says so when the list cannot be fetched', async () => {
		api.recommendation.getSaved.mockRejectedValue(new Error('offline'));
		const view = readLaterPage();

		await waitFor(() => expect(view.listError()).not.toBeNull());
	});

	it('appends the next page from where the list stops', async () => {
		api.recommendation.getSaved.mockResolvedValue(
			Array.from({ length: PAGE_SIZE }, (_, index) => articleSummary(`saved-${index}`))
		);
		const view = readLaterPage();
		await waitFor(() => expect(view.loadMore()).not.toBeNull());
		api.recommendation.getSaved.mockResolvedValue([articleSummary('later')]);

		await fireEvent.click(view.loadMore()!);

		await waitFor(() => expect(view.card('later')).not.toBeNull());
		expect(api.recommendation.getSaved).toHaveBeenLastCalledWith(PAGE_SIZE, PAGE_SIZE);
	});

	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		readLaterPage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(api.recommendation.getSaved).not.toHaveBeenCalled();
	});
});

describe('saving a url by hand', () => {
	it('extracts the page, clears the field and refreshes the list', async () => {
		const view = readLaterPage();
		await waitFor(() => expect(view.card('saved-1')).not.toBeNull());
		api.article.saveUrl.mockResolvedValue(articleDetail('saved-2', { title: 'Un article' }));
		api.recommendation.getSaved.mockResolvedValue([
			articleSummary('saved-1'),
			articleSummary('saved-2')
		]);

		await fireEvent.input(view.url(), { target: { value: '  https://example.test/page  ' } });
		await fireEvent.submit(view.saveForm());

		await waitFor(() => expect(api.article.saveUrl).toHaveBeenCalledWith('https://example.test/page'));
		await waitFor(() => expect(view.card('saved-2')).not.toBeNull());
		expect(view.url().value).toBe('');
	});

	// A url the extractor choked on has to stay in the field, or the reader loses what they pasted.
	it('keeps the url and explains the failure when extraction fails', async () => {
		const view = readLaterPage();
		await waitFor(() => expect(view.card('saved-1')).not.toBeNull());
		api.article.saveUrl.mockRejectedValue(new Error('unreachable'));

		await fireEvent.input(view.url(), { target: { value: 'https://example.test/page' } });
		await fireEvent.submit(view.saveForm());

		await waitFor(() => expect(view.saveError()).not.toBeNull());
		expect(view.url().value).toBe('https://example.test/page');
	});

	it('saves nothing from a blank field', async () => {
		const view = readLaterPage();
		await waitFor(() => expect(view.card('saved-1')).not.toBeNull());

		await fireEvent.submit(view.saveForm());

		expect(api.article.saveUrl).not.toHaveBeenCalled();
	});
});
