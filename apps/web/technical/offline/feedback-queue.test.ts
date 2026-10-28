import { beforeEach, describe, expect, it } from 'vitest';
import { articleDetail } from '../../src/routes/test-support/fixtures';
import { freshOfflineDatabase } from '../../test-support/fresh-offline-database';
import { getStoredArticle, putStoredArticles } from './article-store';
import {
	clearPendingFeedback,
	listPendingFeedback,
	mergeFeedback,
	queueFeedback
} from './feedback-queue';

beforeEach(freshOfflineDatabase);

describe('mergeFeedback', () => {
	it('keeps the last value of every axis', () => {
		expect(mergeFeedback({ sentiment: 'like', saved: true }, { sentiment: 'dislike' })).toEqual({
			sentiment: 'dislike',
			saved: true
		});
	});

	it('lets a cleared vote win over an earlier one', () => {
		expect(mergeFeedback({ sentiment: 'like' }, { sentiment: null })).toEqual({ sentiment: null });
	});

	it('never lets reading progress go back', () => {
		expect(mergeFeedback({ scroll_progress: 0.8 }, { scroll_progress: 0.3 })).toEqual({
			scroll_progress: 0.8
		});
		expect(mergeFeedback({ scroll_progress: 0.3 }, { scroll_progress: 0.8 })).toEqual({
			scroll_progress: 0.8
		});
	});
});

describe('queueFeedback', () => {
	it('holds one entry per article, merged', async () => {
		await queueFeedback('a1', { sentiment: 'like' });
		await queueFeedback('a1', { read: true });
		await queueFeedback('a2', { sentiment: 'dislike' });

		const pending = await listPendingFeedback();

		expect(pending.map((entry) => [entry.articleId, entry.update])).toEqual([
			['a1', { sentiment: 'like', read: true }],
			['a2', { sentiment: 'dislike' }]
		]);
	});

	it('moves the revision on every write', async () => {
		await queueFeedback('a1', { read: true });
		await queueFeedback('a1', { saved: true });

		expect((await listPendingFeedback())[0].revision).toBe(2);
	});

	it('records where reading stopped on the stored copy, so reopening offline resumes there', async () => {
		await putStoredArticles([
			{ id: 'a1', article: articleDetail('a1', { scroll_progress: 0.2 }), listedAs: 'saved' }
		]);

		await queueFeedback('a1', { scroll_progress: 0.6, read: true });
		await queueFeedback('a1', { scroll_progress: 0.4 });

		const stored = await getStoredArticle('a1');
		expect(stored?.article.scroll_progress).toBe(0.6);
		expect(stored?.article.read).toBe(true);
	});
});

describe('clearPendingFeedback', () => {
	it('removes the entry it was told about', async () => {
		await queueFeedback('a1', { read: true });
		const [entry] = await listPendingFeedback();

		await clearPendingFeedback('a1', entry.revision);

		expect(await listPendingFeedback()).toEqual([]);
	});

	it('keeps an entry rewritten while the earlier one was being sent', async () => {
		await queueFeedback('a1', { sentiment: 'like' });
		const [sent] = await listPendingFeedback();
		await queueFeedback('a1', { sentiment: 'dislike' });

		await clearPendingFeedback('a1', sent.revision);

		const [left] = await listPendingFeedback();
		expect(left.update).toEqual({ sentiment: 'dislike' });
	});
});
