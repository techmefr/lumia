import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import { articleSummary } from '../test-support/fixtures';
import FavoritesPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		recommendation: { getFavorites: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

const PAGE_SIZE = 24;

function fullPage(prefix: string) {
	return Array.from({ length: PAGE_SIZE }, (_, index) => articleSummary(`${prefix}${index}`));
}

function favoritesPage() {
	const { container } = render(FavoritesPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		error: () => q('[role="alert"]'),
		cards: () => [...container.querySelectorAll('[data-test-article-card]')],
		card: (id: string) => q(`[data-test-article-card="${id}"]`),
		browse: () => q<HTMLAnchorElement>('a[href$="/articles"]'),
		loadMore: () => q<HTMLButtonElement>('[data-test-load-more]')
	};
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.recommendation.getFavorites.mockResolvedValue([articleSummary('fav-1')]);
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('the favourites list', () => {
	it('shows the articles the reader starred', async () => {
		const view = favoritesPage();

		await waitFor(() => expect(view.card('fav-1')).not.toBeNull());
		expect(api.recommendation.getFavorites).toHaveBeenCalledWith(PAGE_SIZE, 0);
	});

	it('points an empty list back at the article list', async () => {
		api.recommendation.getFavorites.mockResolvedValue([]);
		const view = favoritesPage();

		await waitFor(() => expect(view.browse()).not.toBeNull());
		expect(view.cards()).toHaveLength(0);
	});

	it('says so when the favourites cannot be fetched', async () => {
		api.recommendation.getFavorites.mockRejectedValue(new Error('offline'));
		const view = favoritesPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		favoritesPage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(api.recommendation.getFavorites).not.toHaveBeenCalled();
	});
});

describe('paging through the favourites', () => {
	// A short page means the end: offering more there would send the reader to an empty request.
	it('offers no next page when the first one came back short', async () => {
		const view = favoritesPage();
		await waitFor(() => expect(view.cards()).toHaveLength(1));

		expect(view.loadMore()).toBeNull();
	});

	it('appends the next page from where the list stops', async () => {
		api.recommendation.getFavorites.mockResolvedValue(fullPage('fav-'));
		const view = favoritesPage();
		await waitFor(() => expect(view.loadMore()).not.toBeNull());
		api.recommendation.getFavorites.mockResolvedValue([articleSummary('later')]);

		await fireEvent.click(view.loadMore()!);

		await waitFor(() => expect(view.card('later')).not.toBeNull());
		expect(api.recommendation.getFavorites).toHaveBeenLastCalledWith(PAGE_SIZE, PAGE_SIZE);
		expect(view.cards()).toHaveLength(PAGE_SIZE + 1);
	});

	it('keeps what is on screen when the next page fails', async () => {
		api.recommendation.getFavorites.mockResolvedValue(fullPage('fav-'));
		const view = favoritesPage();
		await waitFor(() => expect(view.loadMore()).not.toBeNull());
		api.recommendation.getFavorites.mockRejectedValue(new Error('offline'));

		await fireEvent.click(view.loadMore()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.cards()).toHaveLength(PAGE_SIZE);
	});
});
