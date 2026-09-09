import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import type { TokenStore } from '../../technical/token-store';
import { createUserApi } from './api';

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

const TOKENS = { access_token: 'access-1', refresh_token: 'refresh-1' };

function api(replies: unknown[] = [], initial: Parameters<typeof memoryStore>[0] = {}) {
	const recorder = recordingHttpClient(replies);
	const store = memoryStore(initial);
	return { ...recorder, store, user: createUserApi(recorder.http, store) };
}

describe('login', () => {
	it('posts the credentials unauthenticated, since there is no session yet', async () => {
		const { user, last } = api([TOKENS]);
		await user.login('lena@lumia.test', 'correct horse');
		expect(last()).toMatchObject({
			path: '/auth/login',
			method: 'POST',
			body: { email: 'lena@lumia.test', password: 'correct horse' },
			auth: false
		});
	});

	it('opens the session, so the next call is authenticated', async () => {
		const { user, store } = api([TOKENS]);
		await user.login('lena@lumia.test', 'correct horse');
		expect(store.getAccessToken()).toBe('access-1');
		expect(store.getRefreshToken()).toBe('refresh-1');
		expect(user.isAuthenticated()).toBe(true);
	});

	it('leaves no session behind when the credentials are refused', async () => {
		const recorder = recordingHttpClient();
		const store = memoryStore();
		recorder.http.request = async () => {
			throw new Error('API error 401');
		};
		const user = createUserApi(recorder.http, store);
		await expect(user.login('lena@lumia.test', 'wrong')).rejects.toThrow();
		expect(user.isAuthenticated()).toBe(false);
	});
});

describe('isAuthenticated', () => {
	it('is false with no token', () => {
		expect(api().user.isAuthenticated()).toBe(false);
	});

	it('is true as soon as an access token is held', () => {
		expect(api([], { access: 'access-1' }).user.isAuthenticated()).toBe(true);
	});

	it('is false on a refresh token alone: it cannot open a request', () => {
		expect(api([], { refresh: 'refresh-1' }).user.isAuthenticated()).toBe(false);
	});
});

describe('logout', () => {
	it('revokes the refresh token server-side and drops the local session', async () => {
		const { user, store, last } = api([undefined], {
			access: 'access-1',
			refresh: 'refresh-1'
		});
		await user.logout();
		expect(last()).toMatchObject({
			path: '/auth/logout',
			method: 'POST',
			body: { refresh_token: 'refresh-1' }
		});
		expect(user.isAuthenticated()).toBe(false);
		expect(store.getRefreshToken()).toBeNull();
	});

	it('skips the call when there is nothing to revoke, but still clears', async () => {
		const { user, requests } = api([], { access: 'access-1' });
		await user.logout();
		expect(requests).toEqual([]);
		expect(user.isAuthenticated()).toBe(false);
	});

	// Someone on a shared machine pressing "log out" must end up logged out on that machine even
	// when the revoke call cannot reach the server. The failure still surfaces, so the interface can
	// say the server-side token was not revoked, but the local session is gone either way.
	it('logs out locally even when the server cannot be reached', async () => {
		const recorder = recordingHttpClient();
		const store = memoryStore({ access: 'access-1', refresh: 'refresh-1' });
		recorder.http.request = async () => {
			throw new Error('network down');
		};
		const user = createUserApi(recorder.http, store);

		await expect(user.logout()).rejects.toThrow('network down');
		expect(user.isAuthenticated()).toBe(false);
		expect(store.getRefreshToken()).toBeNull();
	});
});

describe('the magic link', () => {
	it('requests one unauthenticated, which is the point of it', async () => {
		const { user, last } = api([undefined]);
		await user.requestMagicLink('lena@lumia.test');
		expect(last()).toMatchObject({
			path: '/auth/magic-link',
			method: 'POST',
			body: { email: 'lena@lumia.test' },
			auth: false
		});
	});

	it('opens the session when the token checks out', async () => {
		const { user, last } = api([TOKENS]);
		await user.verifyMagicLink('token-abc');
		expect(last()).toMatchObject({ path: '/auth/magic-link/verify', auth: false });
		expect(user.isAuthenticated()).toBe(true);
	});
});

describe('onboardAdmin', () => {
	it('posts the first account unauthenticated and signs it straight in', async () => {
		const { user, last } = api([TOKENS]);
		await user.onboardAdmin({
			email: 'lena@lumia.test',
			username: 'lena',
			password: 'correct horse'
		});
		expect(last()).toMatchObject({ path: '/onboarding/admin', method: 'POST', auth: false });
		expect(user.isAuthenticated()).toBe(true);
	});

	it('passes the optional quotas through when given', async () => {
		const { user, last } = api([TOKENS]);
		await user.onboardAdmin({
			email: 'lena@lumia.test',
			username: 'lena',
			password: 'correct horse',
			max_accounts: 4,
			disk_quota_mb: 2048
		});
		expect(last().body).toMatchObject({ max_accounts: 4, disk_quota_mb: 2048 });
	});
});

describe('the profile', () => {
	it('reads it from /me', async () => {
		const { user, last } = api([{ email: 'lena@lumia.test' }]);
		await expect(user.getMe()).resolves.toEqual({ email: 'lena@lumia.test' });
		expect(last()).toMatchObject({ path: '/me', method: 'GET' });
	});

	it('patches only what changed', async () => {
		const { user, last } = api([{ email: 'lena@lumia.test' }]);
		await user.updateMe({ preferred_language: 'es' });
		expect(last()).toMatchObject({
			path: '/me',
			method: 'PATCH',
			body: { preferred_language: 'es' }
		});
	});
});
