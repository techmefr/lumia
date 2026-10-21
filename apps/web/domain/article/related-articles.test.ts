import { cleanup, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { articleSummary } from '../../src/routes/test-support/fixtures';
import RelatedArticles from './related-articles.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { article: { getRelatedArticles: vi.fn() } }
}));

const api = vi.mocked(lumia, { deep: true });

afterEach(() => {
	cleanup();
	vi.resetAllMocks();
});

describe('RelatedArticles', () => {
	it('lists each related article under a heading', async () => {
		api.article.getRelatedArticles.mockResolvedValue([
			articleSummary('a-2'),
			articleSummary('a-3')
		]);
		const { container } = render(RelatedArticles, { articleId: 'a-1' });

		await waitFor(() =>
			expect(container.querySelectorAll('[data-test-related-item]')).toHaveLength(2)
		);
		expect(api.article.getRelatedArticles).toHaveBeenCalledWith('a-1');
		expect(container.querySelector('h2')).not.toBeNull();
	});

	it('renders nothing when there are no related articles', async () => {
		api.article.getRelatedArticles.mockResolvedValue([]);
		const { container } = render(RelatedArticles, { articleId: 'a-1' });

		await waitFor(() => expect(api.article.getRelatedArticles).toHaveBeenCalled());
		expect(container.querySelector('[data-test-related]')).toBeNull();
	});

	it('renders nothing when the lookup fails', async () => {
		api.article.getRelatedArticles.mockRejectedValue(new Error('boom'));
		const { container } = render(RelatedArticles, { articleId: 'a-1' });

		await waitFor(() => expect(api.article.getRelatedArticles).toHaveBeenCalled());
		expect(container.querySelector('[data-test-related]')).toBeNull();
	});
});
