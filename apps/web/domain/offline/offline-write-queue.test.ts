import { describe, expect, it, vi } from 'vitest';
import type { FeedbackUpdate } from '@lumia/core';
import { createInMemoryOfflineDatabase } from '$technical/offline/in-memory-offline-database';
import { OfflineWriteQueue } from './offline-write-queue.svelte';

describe('OfflineWriteQueue', () => {
	it('starts empty', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.init();
		expect(queue.pendingCount).toBe(0);
	});

	it('queues a write made while offline', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.enqueue('a1', { scroll_progress: 0.4 });
		expect(queue.pendingCount).toBe(1);
	});

	it('merges a second write for the same article instead of piling up a new entry', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.enqueue('a1', { scroll_progress: 0.2 });
		await queue.enqueue('a1', { scroll_progress: 0.6 });
		expect(queue.pendingCount).toBe(1);
		expect(queue.pending[0].payload).toEqual({ scroll_progress: 0.6 });
	});

	it('keeps writes for different articles independent, even when coalesced', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.enqueue('a1', { saved: true });
		await queue.enqueue('a2', { favorite: true });
		expect(queue.pendingCount).toBe(2);
	});

	it('preserves fields a later write did not touch when coalescing', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.enqueue('a1', { saved: true });
		await queue.enqueue('a1', { scroll_progress: 0.5 });
		expect(queue.pending[0].payload).toEqual({ saved: true, scroll_progress: 0.5 });
	});

	it('replays every pending write, oldest first, and clears them on success', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.enqueue('a1', { read: true });
		await queue.enqueue('a2', { favorite: true });
		const sent: Array<[string, FeedbackUpdate]> = [];
		const result = await queue.flush(async (articleId, payload) => {
			sent.push([articleId, payload]);
		});
		expect(result).toEqual({ synced: 2, remaining: 0 });
		expect(sent).toEqual([
			['a1', { read: true }],
			['a2', { favorite: true }]
		]);
		expect(queue.pendingCount).toBe(0);
	});

	it('stops at the first failure and leaves the rest queued for the next attempt', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.enqueue('a1', { read: true });
		await queue.enqueue('a2', { favorite: true });
		const sendFeedback = vi.fn().mockRejectedValueOnce(new Error('offline again'));
		const result = await queue.flush(sendFeedback);
		expect(result).toEqual({ synced: 0, remaining: 2 });
		expect(sendFeedback).toHaveBeenCalledTimes(1);
	});

	it('a vote replayed twice cannot count double: the payload is the end state, not a delta', async () => {
		const queue = new OfflineWriteQueue(createInMemoryOfflineDatabase());
		await queue.enqueue('a1', { sentiment: 'like' });
		const sent: FeedbackUpdate[] = [];
		await queue.flush(async (_articleId, payload) => {
			sent.push(payload);
		});
		await queue.enqueue('a1', { sentiment: 'like' });
		await queue.flush(async (_articleId, payload) => {
			sent.push(payload);
		});
		expect(sent).toEqual([{ sentiment: 'like' }, { sentiment: 'like' }]);
	});
});
