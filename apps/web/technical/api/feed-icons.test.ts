import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { feedIcons } from './feed-icons.svelte';
import { lumia } from './client';

/**
 * The network is the outer boundary and the only thing stubbed. Everything asserted below is what
 * the store returns to a card asking for an icon.
 */
function respond(replies: Array<{ ok: boolean } | Error>) {
	const calls: Array<{ url: string; token: string | undefined }> = [];
	const queue = [...replies];

	vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
		const headers = (init?.headers ?? {}) as Record<string, string>;
		calls.push({ url, token: headers.authorization });
		const reply = queue.shift();
		if (reply instanceof Error) throw reply;
		if (!reply) throw new Error(`no reply queued for ${url}`);
		return { ok: reply.ok, blob: async () => new Blob(['icon']) } as Response;
	});

	return calls;
}

let created: Blob[] = [];

beforeEach(() => {
	created = [];
	// Patched onto URL rather than replacing it: jsdom implements no object urls, but `new URL()`
	// is used all over the code under test, so the constructor has to survive.
	Object.defineProperty(URL, 'createObjectURL', {
		configurable: true,
		writable: true,
		value: (blob: Blob) => {
			created.push(blob);
			return `blob:icon-${created.length}`;
		}
	});
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.restoreAllMocks();
	Reflect.deleteProperty(URL, 'createObjectURL');
});

/** The fetch is fired but not awaited by `get`, so the test waits for the url to turn up. */
async function iconOf(feedId: string): Promise<string | null> {
	feedIcons.get(feedId);
	await vi.waitFor(() => {
		if (feedIcons.get(feedId) === null) throw new Error('not resolved yet');
	});
	return feedIcons.get(feedId);
}

describe('asking for an icon', () => {
	// The card asks synchronously while rendering, so the first answer is always "nothing yet" and
	// the fetch happens behind it. Returning a promise instead would mean a card that cannot draw
	// until the network answers.
	it('answers nothing on the first ask and fetches behind it', () => {
		const calls = respond([{ ok: true }]);

		expect(feedIcons.get('feed-first')).toBeNull();
		expect(calls).toHaveLength(1);
	});

	it('answers the object url once the icon has arrived', async () => {
		respond([{ ok: true }]);
		expect(await iconOf('feed-arrived')).toBe('blob:icon-1');
	});

	// An `<img src>` cannot carry an Authorization header, which is the entire reason this store
	// exists: the icon is proxied behind bearer auth, so it has to be fetched by hand.
	it('sends the access token, since the proxy is behind auth', () => {
		vi.spyOn(lumia.tokenStore, 'getAccessToken').mockReturnValue('a-token');
		const calls = respond([{ ok: true }]);

		feedIcons.get('feed-token');

		expect(calls[0].token).toBe('Bearer a-token');
	});

	it('asks anyway when there is no token, rather than not showing icons at all', () => {
		vi.spyOn(lumia.tokenStore, 'getAccessToken').mockReturnValue(null);
		const calls = respond([{ ok: true }]);

		feedIcons.get('feed-anon');

		expect(calls[0].token).toBeUndefined();
	});

	it('asks the api for the icon of the feed it was given', () => {
		const calls = respond([{ ok: true }]);

		feedIcons.get('feed-url');

		expect(calls[0].url).toContain('/feeds/feed-url/icon');
	});
});

describe('caching', () => {
	// One fetch per feed for the life of the page: the icon appears on every card of a feed, and a
	// list of twenty-four articles from one source would otherwise hit the proxy twenty-four times.
	it('fetches once however many cards ask', async () => {
		const calls = respond([{ ok: true }]);
		await iconOf('feed-cached');

		feedIcons.get('feed-cached');
		feedIcons.get('feed-cached');

		expect(calls).toHaveLength(1);
	});

	it('does not fire a second fetch while the first is in flight', () => {
		const calls = respond([{ ok: true }]);

		feedIcons.get('feed-inflight');
		feedIcons.get('feed-inflight');
		feedIcons.get('feed-inflight');

		expect(calls).toHaveLength(1);
	});

	it('keeps the icons of different feeds apart', async () => {
		respond([{ ok: true }, { ok: true }]);

		const first = await iconOf('feed-a');
		const second = await iconOf('feed-b');

		expect(first).not.toBe(second);
	});
});

describe('in the demo build', () => {
	// There is no api behind the demo page, so asking would be a guaranteed network error on every
	// card. It gives up before the fetch and the cards fall back to the source initial.
	it('never goes to the network', async () => {
		vi.stubEnv('VITE_DEMO', 'true');
		vi.resetModules();
		const calls = respond([{ ok: true }]);

		const { feedIcons: demoIcons } = await import('./feed-icons.svelte');
		demoIcons.get('feed-demo');
		demoIcons.get('feed-demo');

		expect(calls).toHaveLength(0);
		expect(demoIcons.get('feed-demo')).toBeNull();
		vi.unstubAllEnvs();
		vi.resetModules();
	});
});

describe('when there is no icon to be had', () => {
	// A feed with no icon is the common case, not an error: the card falls back to the source
	// initial, and asking again on every render would hammer the proxy for a 404 it already knows.
	it('gives up on a feed the api has no icon for, and does not ask again', async () => {
		const calls = respond([{ ok: false }]);

		feedIcons.get('feed-missing');
		await vi.waitFor(() => expect(calls).toHaveLength(1));

		feedIcons.get('feed-missing');
		feedIcons.get('feed-missing');

		expect(calls).toHaveLength(1);
		expect(feedIcons.get('feed-missing')).toBeNull();
	});

	it('gives up the same way when the network throws', async () => {
		const calls = respond([new Error('offline')]);

		feedIcons.get('feed-offline');
		await vi.waitFor(() => expect(calls).toHaveLength(1));

		feedIcons.get('feed-offline');

		expect(calls).toHaveLength(1);
		expect(feedIcons.get('feed-offline')).toBeNull();
	});
});
