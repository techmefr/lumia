import { ApiError, type FeedbackUpdate } from '@lumia/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { freshOfflineDatabase } from '../../test-support/fresh-offline-database';
import { listPendingFeedback } from './feedback-queue';
import { MAX_ATTEMPTS, createFeedbackSync } from './feedback-sync';

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

describe('poisoned entries', () => {
	async function queuedThenOnline(ids: string[]) {
		const dropped: [string, string][] = [];
		const ctx = setup(false);
		const sync = createFeedbackSync(
			ctx.send,
			() => ctx.state.online,
			() => null,
			(id, reason) => dropped.push([id, reason])
		);
		for (const id of ids) await sync.submit(id, { read: true });
		ctx.state.online = true;
		return { ...ctx, sync, dropped };
	}

	it.each([400, 403, 413, 422, 404])('purges an entry refused with %i and sends the next', async (status) => {
		const { sync, state, sent, dropped } = await queuedThenOnline(['bad', 'ok']);
		state.failureFor.set('bad', new ApiError(status, {}));

		await sync.flush();

		expect(sent.map((entry) => entry.articleId)).toEqual(['ok']);
		expect(await listPendingFeedback()).toEqual([]);
		expect(dropped).toEqual([['bad', 'rejected']]);
	});

	it.each([401, 429, 500])('bounds retries on %i without blocking later entries', async (status) => {
		const { sync, state, sent, dropped } = await queuedThenOnline(['stuck', 'ok']);
		state.failureFor.set('stuck', new ApiError(status, {}));

		await sync.flush();
		expect(sent.map((entry) => entry.articleId)).toEqual(['ok']);
		expect((await listPendingFeedback()).map((entry) => entry.articleId)).toEqual(['stuck']);
		expect(dropped).toEqual([]);

		for (let i = 1; i < MAX_ATTEMPTS; i++) await sync.flush();

		expect(await listPendingFeedback()).toEqual([]);
		expect(dropped).toEqual([['stuck', 'exhausted']]);
	});

	it('never replays an entry queued by another user', async () => {
		const ctx = setup(false);
		let owner: string | null = 'alice';
		const sync = createFeedbackSync(ctx.send, () => ctx.state.online, () => owner);
		await sync.submit('a1', { read: true });
		owner = 'bob';
		ctx.state.online = true;

		await sync.flush();

		expect(ctx.send).not.toHaveBeenCalled();
		expect(await listPendingFeedback()).toEqual([]);
	});

	it('keeps the owner on queued entries and replaces a foreign entry instead of merging', async () => {
		const ctx = setup(false);
		let owner: string | null = 'alice';
		const sync = createFeedbackSync(ctx.send, () => ctx.state.online, () => owner);
		await sync.submit('a1', { sentiment: 'like' });
		owner = 'bob';
		await sync.submit('a1', { read: true });

		const [entry] = await listPendingFeedback();
		expect(entry.owner).toBe('bob');
		expect(entry.update).toEqual({ read: true });
	});
});

describe('submit while online with a transient server failure', () => {
	it.each([500, 502, 503, 429, 408])('queues the write on %i instead of losing it', async (status) => {
		const { sync, state } = setup();
		state.failure = new ApiError(status, {});

		await sync.submit('a1', { read: true });

		expect((await listPendingFeedback())[0].update).toEqual({ read: true });
	});

	it('still surfaces a definitive refusal', async () => {
		const { sync, state } = setup();
		state.failure = new ApiError(403, {});

		await expect(sync.submit('a1', { read: true })).rejects.toBeInstanceOf(ApiError);
	});
});
