import { ApiError, type FeedbackUpdate } from '@lumia/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { freshOfflineDatabase } from '../../test-support/fresh-offline-database';
import { listPendingFeedback } from './feedback-queue';
import { createFeedbackSync } from './feedback-sync';

interface Sent {
	articleId: string;
	update: FeedbackUpdate;
}

function setup(initiallyOnline = true) {
	const sent: Sent[] = [];
	const state = {
		online: initiallyOnline,
		failure: null as unknown,
		failureFor: new Map<string, unknown>()
	};
	const send = vi.fn(async (articleId: string, update: FeedbackUpdate) => {
		if (state.failure) throw state.failure;
		if (state.failureFor.has(articleId)) throw state.failureFor.get(articleId);
		sent.push({ articleId, update });
	});
	const sync = createFeedbackSync(send, () => state.online);
	return { sync, sent, state, send };
}

beforeEach(freshOfflineDatabase);

describe('submit while online', () => {
	it('sends straight away and queues nothing', async () => {
		const { sync, sent } = setup();

		await sync.submit('a1', { sentiment: 'like' });

		expect(sent).toEqual([{ articleId: 'a1', update: { sentiment: 'like' } }]);
		expect(await listPendingFeedback()).toEqual([]);
	});

	it('queues instead when the network drops mid-request', async () => {
		const { sync, state, sent } = setup();
		state.failure = new TypeError('Failed to fetch');

		await sync.submit('a1', { read: true });

		expect(sent).toEqual([]);
		expect((await listPendingFeedback())[0].update).toEqual({ read: true });
	});

	it('lets a refusal from the server through rather than hiding it in the queue', async () => {
		const { sync, state } = setup();
		state.failure = new ApiError(401, {});

		await expect(sync.submit('a1', { read: true })).rejects.toBeInstanceOf(ApiError);
		expect(await listPendingFeedback()).toEqual([]);
	});
});

describe('submit while offline', () => {
	it('queues without calling the server', async () => {
		const { sync, send } = setup(false);

		await sync.submit('a1', { sentiment: 'like' });

		expect(send).not.toHaveBeenCalled();
		expect(await listPendingFeedback()).toHaveLength(1);
	});

	it('folds a read mark, a vote and the furthest position into one replayed update', async () => {
		const { sync, state, sent } = setup(false);

		await sync.submit('a1', { scroll_progress: 0.3 });
		await sync.submit('a1', { sentiment: 'like' });
		await sync.submit('a1', { scroll_progress: 0.95 });
		await sync.submit('a1', { read: true });
		state.online = true;
		await sync.flush();

		expect(sent).toEqual([
			{ articleId: 'a1', update: { scroll_progress: 0.95, sentiment: 'like', read: true } }
		]);
	});
});

describe('flush', () => {
	it('empties the queue once the server has taken everything', async () => {
		const { sync, state } = setup(false);
		await sync.submit('a1', { sentiment: 'like' });
		await sync.submit('a2', { read: true });
		state.online = true;

		await sync.flush();

		expect(await listPendingFeedback()).toEqual([]);
	});

	it('does nothing while still offline', async () => {
		const { sync, send } = setup(false);
		await sync.submit('a1', { read: true });

		await sync.flush();

		expect(send).not.toHaveBeenCalled();
		expect(await listPendingFeedback()).toHaveLength(1);
	});

	it('keeps what it could not send and stops at the first failure', async () => {
		const { sync, state, send } = setup(false);
		await sync.submit('a1', { sentiment: 'like' });
		await sync.submit('a2', { sentiment: 'like' });
		state.online = true;
		state.failure = new TypeError('Failed to fetch');

		await sync.flush();

		expect(send).toHaveBeenCalledTimes(1);
		expect(await listPendingFeedback()).toHaveLength(2);
	});

	it('drops an entry the server says no longer exists, so it cannot block the rest', async () => {
		const { sync, state, sent } = setup(false);
		await sync.submit('gone', { read: true });
		await sync.submit('a2', { read: true });
		state.online = true;
		state.failureFor.set('gone', new ApiError(404, {}));

		await sync.flush();

		expect(sent.map((entry) => entry.articleId)).toEqual(['a2']);
		expect(await listPendingFeedback()).toEqual([]);
	});

	it('replays a vote as the value to hold, so sending it twice leaves one vote', async () => {
		const { sync, state, sent } = setup(false);
		await sync.submit('a1', { sentiment: 'like' });
		state.online = true;
		state.failure = new TypeError('Failed to fetch');
		await sync.flush();
		state.failure = null;

		await sync.flush();
		await sync.flush();

		expect(sent).toEqual([{ articleId: 'a1', update: { sentiment: 'like' } }]);
	});

	it('shares one run between two callers', async () => {
		const { sync, state, send } = setup(false);
		await sync.submit('a1', { read: true });
		state.online = true;

		await Promise.all([sync.flush(), sync.flush()]);

		expect(send).toHaveBeenCalledTimes(1);
	});
});

describe('submit with entries already waiting', () => {
	it('flushes them first, so an older value never lands on top of a newer one', async () => {
		const { sync, state, sent } = setup(false);
		await sync.submit('a1', { sentiment: 'like' });
		state.online = true;

		await sync.submit('a1', { sentiment: 'dislike' });

		expect(sent.map((entry) => entry.update)).toEqual([
			{ sentiment: 'like' },
			{ sentiment: 'dislike' }
		]);
	});

	it('keeps the new value behind the old one while the old one cannot be sent', async () => {
		const { sync, state, sent } = setup(false);
		await sync.submit('a1', { sentiment: 'like' });
		state.online = true;
		state.failure = new TypeError('Failed to fetch');

		await sync.submit('a1', { sentiment: 'dislike' });
		state.failure = null;
		await sync.flush();

		expect(sent.map((entry) => entry.update)).toEqual([{ sentiment: 'dislike' }]);
	});
});

describe('without browser storage', () => {
	it('sends directly', async () => {
		vi.stubGlobal('indexedDB', undefined);
		const { sync, sent } = setup();

		await sync.submit('a1', { read: true });
		vi.unstubAllGlobals();

		expect(sent).toHaveLength(1);
	});
});
