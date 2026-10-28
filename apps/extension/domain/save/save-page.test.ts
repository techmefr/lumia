import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLumiaClient, type LumiaClient, type TokenStore } from '@lumia/core';
import { stubFetch } from '$test-support/stub-fetch';
import { savePage } from './save-page';

function memoryTokens(access: string | null, refresh: string | null): TokenStore {
	let accessToken = access;
	let refreshToken = refresh;
	return {
		getAccessToken: () => accessToken,
		getRefreshToken: () => refreshToken,
		setTokens: (tokens) => {
			accessToken = tokens.accessToken;
			refreshToken = tokens.refreshToken;
		},
		setAccessToken: (token) => {
			accessToken = token;
		},
		clear: () => {
			accessToken = null;
			refreshToken = null;
		}
	};
}

function signedInClient(): LumiaClient {
	return createLumiaClient('https://lumia.test/api', memoryTokens('access', 'refresh'));
}

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('savePage', () => {
	it('posts the page address with the token and reports a new save', async () => {
		const { requests } = stubFetch([{ status: 201, body: { id: 'a1', already_saved: false } }]);
		expect(await savePage(signedInClient(), 'https://blog.test/post')).toBe('saved');
		expect(requests).toEqual([
			{
				url: 'https://lumia.test/api/articles/save-url',
				method: 'POST',
				body: { url: 'https://blog.test/post' },
				authorization: 'Bearer access'
			}
		]);
	});

	it('tells a page that was already in the list apart from a new one', async () => {
		stubFetch([{ status: 201, body: { id: 'a1', already_saved: true } }]);
		expect(await savePage(signedInClient(), 'https://blog.test/post')).toBe('already_saved');
	});

	it.each(['chrome://extensions', 'about:blank', 'not a url', 'file:///tmp/a.html', undefined])(
		'refuses %s without calling the instance',
		async (url) => {
			const { requests } = stubFetch([]);
			expect(await savePage(signedInClient(), url)).toBe('unsupported');
			expect(requests).toEqual([]);
		}
	);

	it('asks for the instance address when none is set', async () => {
		expect(await savePage(null, 'https://blog.test/post')).toBe('unconfigured');
	});

	it('asks to sign in when there is no token at all, without a request', async () => {
		const { requests } = stubFetch([]);
		const client = createLumiaClient('https://lumia.test/api', memoryTokens(null, null));
		expect(await savePage(client, 'https://blog.test/post')).toBe('unauthenticated');
		expect(requests).toEqual([]);
	});

	it('asks to sign in again when the session cannot be refreshed', async () => {
		stubFetch([{ status: 401 }, { status: 401 }]);
		expect(await savePage(signedInClient(), 'https://blog.test/post')).toBe('unauthenticated');
	});

	it('saves after a silent refresh of the short-lived token', async () => {
		const { requests } = stubFetch([
			{ status: 401 },
			{ status: 200, body: { access_token: 'new-access', refresh_token: 'new-refresh' } },
			{ status: 201, body: { id: 'a1', already_saved: false } }
		]);
		expect(await savePage(signedInClient(), 'https://blog.test/post')).toBe('saved');
		expect(requests[2].authorization).toBe('Bearer new-access');
	});

	it('reports a failure when the instance cannot read the page', async () => {
		stubFetch([{ status: 400 }]);
		expect(await savePage(signedInClient(), 'https://blog.test/post')).toBe('failed');
	});

	it('reports a failure when the instance is unreachable', async () => {
		stubFetch([new TypeError('network down')]);
		expect(await savePage(signedInClient(), 'https://blog.test/post')).toBe('failed');
	});
});
