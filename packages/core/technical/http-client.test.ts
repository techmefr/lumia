import { afterEach, describe, expect, it } from 'vitest';
import { ApiError, createHttpClient } from './http-client';
import type { TokenStore } from './token-store';

/** An in-memory store: the client's contract is with the interface, not with localStorage. */
function memoryStore(initial: { access?: string | null; refresh?: string | null } = {}): TokenStore {
	let access = initial.access ?? null;
	let refresh = initial.refresh ?? null;
	return {
		getAccessToken: () => access,
		getRefreshToken: () => refresh,
		setTokens: (tokens) => {
			access = tokens.accessToken;
			refresh = tokens.refreshToken;
		},
		setAccessToken: (token) => {
			access = token;
		},
		clear: () => {
			access = null;
			refresh = null;
		}
	};
}

interface Call {
	url: string;
	method: string;
	headers: Record<string, string>;
	body: unknown;
}

/**
 * A scripted origin rather than a bare mock: each entry answers one request, so the assertions can
 * be about what the client ends up returning and what the server was actually sent.
 */
function scriptedFetch(responses: Response[]) {
	const calls: Call[] = [];
	const remaining = [...responses];
	globalThis.fetch = (async (url: string, init: RequestInit = {}) => {
		calls.push({
			url,
			method: init.method ?? 'GET',
			headers: (init.headers ?? {}) as Record<string, string>,
			body: init.body ?? null
		});
		const next = remaining.shift();
		if (!next) throw new Error(`no scripted response left for ${url}`);
		return next;
	}) as typeof fetch;
	return calls;
}

function json(body: unknown, status = 200) {
	return new Response(JSON.stringify(body), {
		status,
		headers: { 'content-type': 'application/json' }
	});
}

afterEach(() => {
	// @ts-expect-error putting the environment back the way it was found
	delete globalThis.fetch;
});

describe('createHttpClient', () => {
	it('returns the decoded body of a successful request', async () => {
		scriptedFetch([json({ id: 'article-1', title: 'Le retour du web lent' })]);
		const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
		await expect(client.request('/articles/article-1')).resolves.toEqual({
			id: 'article-1',
			title: 'Le retour du web lent'
		});
	});

	it('hits the base url joined to the path', async () => {
		const calls = scriptedFetch([json([])]);
		const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
		await client.request('/articles');
		expect(calls[0].url).toBe('https://lumia.test/articles');
	});

	it('sends the bearer token the store holds', async () => {
		const calls = scriptedFetch([json([])]);
		const client = createHttpClient({
			baseUrl: 'https://lumia.test',
			tokenStore: memoryStore({ access: 'access-1' })
		});
		await client.request('/articles');
		expect(calls[0].headers.authorization).toBe('Bearer access-1');
	});

	it('sends no token when the caller opted out, as the login call does', async () => {
		const calls = scriptedFetch([json({ access_token: 'a', refresh_token: 'r' })]);
		const client = createHttpClient({
			baseUrl: 'https://lumia.test',
			tokenStore: memoryStore({ access: 'access-1' })
		});
		await client.request('/auth/login', { method: 'POST', body: { email: 'a@b.c' }, auth: false });
		expect(calls[0].headers.authorization).toBeUndefined();
	});

	it('serialises a json body and announces its type', async () => {
		const calls = scriptedFetch([json({ ok: true })]);
		const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
		await client.request('/feeds', { method: 'POST', body: { url: 'https://blog.test/rss' } });
		expect(calls[0].body).toBe('{"url":"https://blog.test/rss"}');
		expect(calls[0].headers['content-type']).toBe('application/json');
	});

	it('passes form data through untouched and sets no content type, so the boundary survives', async () => {
		const calls = scriptedFetch([json({ ok: true })]);
		const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
		const formData = new FormData();
		formData.set('file', new Blob(['<opml />']), 'feedly.opml');
		await client.request('/feeds/import', { method: 'POST', formData });
		expect(calls[0].body).toBe(formData);
		expect(calls[0].headers['content-type']).toBeUndefined();
	});

	it('returns undefined on a 204 rather than choking on an empty body', async () => {
		scriptedFetch([new Response(null, { status: 204 })]);
		const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
		await expect(client.request('/articles/article-1/read')).resolves.toBeUndefined();
	});

	describe('an expired access token', () => {
		it('refreshes and replays the request, so the reader sees no interruption', async () => {
			const calls = scriptedFetch([
				json({ detail: 'expired' }, 401),
				json({ access_token: 'access-2', refresh_token: 'refresh-2' }),
				json({ id: 'article-1' })
			]);
			const store = memoryStore({ access: 'access-1', refresh: 'refresh-1' });
			const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: store });

			await expect(client.request('/articles/article-1')).resolves.toEqual({ id: 'article-1' });
			expect(store.getAccessToken()).toBe('access-2');
			expect(calls[2].headers.authorization).toBe('Bearer access-2');
		});

		it('stores the rotated refresh token, so the next refresh is not refused', async () => {
			scriptedFetch([
				json({ detail: 'expired' }, 401),
				json({ access_token: 'access-2', refresh_token: 'refresh-2' }),
				json({ id: 'article-1' })
			]);
			const store = memoryStore({ access: 'access-1', refresh: 'refresh-1' });
			const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: store });

			await client.request('/articles/article-1');

			expect(store.getRefreshToken()).toBe('refresh-2');
		});

		it('gives up without a refresh token instead of looping', async () => {
			const calls = scriptedFetch([json({ detail: 'expired' }, 401)]);
			const client = createHttpClient({
				baseUrl: 'https://lumia.test',
				tokenStore: memoryStore({ access: 'access-1' })
			});
			await expect(client.request('/articles')).rejects.toBeInstanceOf(ApiError);
			expect(calls).toHaveLength(1);
		});

		it('clears the session when the refresh itself is rejected', async () => {
			scriptedFetch([json({ detail: 'expired' }, 401), json({ detail: 'revoked' }, 401)]);
			const store = memoryStore({ access: 'access-1', refresh: 'refresh-1' });
			const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: store });

			await expect(client.request('/articles')).rejects.toBeInstanceOf(ApiError);
			expect(store.getAccessToken()).toBeNull();
			expect(store.getRefreshToken()).toBeNull();
		});

		it('does not retry a 401 the caller asked to send unauthenticated', async () => {
			const calls = scriptedFetch([json({ detail: 'bad credentials' }, 401)]);
			const client = createHttpClient({
				baseUrl: 'https://lumia.test',
				tokenStore: memoryStore({ refresh: 'refresh-1' })
			});
			await expect(client.request('/auth/login', { auth: false })).rejects.toBeInstanceOf(ApiError);
			expect(calls).toHaveLength(1);
		});

		it('retries only once, so a server stuck on 401 does not spin', async () => {
			const calls = scriptedFetch([
				json({ detail: 'expired' }, 401),
				json({ access_token: 'access-2', refresh_token: 'refresh-2' }),
				json({ detail: 'expired again' }, 401)
			]);
			const client = createHttpClient({
				baseUrl: 'https://lumia.test',
				tokenStore: memoryStore({ access: 'access-1', refresh: 'refresh-1' })
			});
			await expect(client.request('/articles')).rejects.toBeInstanceOf(ApiError);
			expect(calls).toHaveLength(3);
		});
	});

	describe('a failing request', () => {
		it('throws an ApiError carrying the status and the body', async () => {
			scriptedFetch([json({ detail: 'feed not found' }, 404)]);
			const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
			await expect(client.request('/feeds/nope')).rejects.toMatchObject({
				status: 404,
				body: { detail: 'feed not found' }
			});
		});

		it('still throws when the error body is not json, with a null body', async () => {
			scriptedFetch([new Response('<html>502</html>', { status: 502 })]);
			const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
			await expect(client.request('/articles')).rejects.toMatchObject({
				status: 502,
				body: null
			});
		});

		it('names the status in the message, which is what ends up in a log', async () => {
			scriptedFetch([json({}, 500)]);
			const client = createHttpClient({ baseUrl: 'https://lumia.test', tokenStore: memoryStore() });
			await expect(client.request('/articles')).rejects.toThrow('API error 500');
		});
	});
});
