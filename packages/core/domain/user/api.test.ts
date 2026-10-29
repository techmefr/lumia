import { describe, expect, it } from 'vitest';
import { ApiError } from '../../technical/http-client';
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
			body: { email: 'lena@lumia.test', purpose: 'sign_in' },
			auth: false
		});
	});

	// The purpose decides which screen the email lands on, so a reset link that says nothing
	// would drop a locked-out reader back on the form they cannot fill.
	it('says when the link is for a forgotten password', async () => {
		const { user, last } = api([undefined]);
		await user.requestMagicLink('lena@lumia.test', 'password_reset');
		expect(last()).toMatchObject({ body: { purpose: 'password_reset' } });
	});

	it('opens the session when the token checks out', async () => {
		const { user, last } = api([TOKENS]);
		await user.verifyMagicLink('token-abc');
		expect(last()).toMatchObject({ path: '/auth/magic-link/verify', auth: false });
		expect(user.isAuthenticated()).toBe(true);
	});
});

describe('changing the password', () => {
	it('posts both passwords to the account route', async () => {
		const { user, last } = api([TOKENS], { access: 'access-0', refresh: 'refresh-0' });
		await user.changePassword('correct horse', 'battery staple');
		expect(last()).toMatchObject({
			path: '/me/password',
			method: 'POST',
			body: { current_password: 'correct horse', new_password: 'battery staple' }
		});
	});

	// The server ends every session on a change, including this one: without keeping the pair it
	// answers with, a reader is signed out of the device they just used to change it.
	it('keeps the device signed in with the pair that comes back', async () => {
		const { user, store } = api([TOKENS], { access: 'access-0', refresh: 'refresh-0' });
		await user.changePassword('correct horse', 'battery staple');
		expect(store.getRefreshToken()).toBe('refresh-1');
	});

	it('sends no current password for an account that has never had one', async () => {
		const { user, last } = api([TOKENS], { access: 'access-0', refresh: 'refresh-0' });
		await user.changePassword(null, 'battery staple');
		expect(last()).toMatchObject({ body: { current_password: null } });
	});
});

describe('resetting a forgotten password', () => {
	it('posts the magic-link token unauthenticated, the reader being locked out', async () => {
		const { user, last } = api([TOKENS]);
		await user.resetPassword('token-abc', 'battery staple');
		expect(last()).toMatchObject({
			path: '/auth/password-reset',
			method: 'POST',
			body: { token: 'token-abc', new_password: 'battery staple' },
			auth: false
		});
	});

	it('opens the session, so the reset lands on a signed-in app', async () => {
		const { user } = api([TOKENS]);
		await user.resetPassword('token-abc', 'battery staple');
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

describe('the fever key', () => {
	it('reads whether one is active from /me/fever', async () => {
		const { user, last } = api([{ enabled: false, created_at: null }]);
		await expect(user.getFeverKey()).resolves.toEqual({ enabled: false, created_at: null });
		expect(last()).toMatchObject({ path: '/me/fever', method: 'GET' });
	});

	it('creates a key with a POST and returns what the server answered', async () => {
		const answer = { email: 'lena@lumia.test', secret: 's3cret', created_at: '2026-10-21T10:00:00Z' };
		const { user, last } = api([answer]);
		await expect(user.createFeverKey()).resolves.toEqual(answer);
		expect(last()).toMatchObject({ path: '/me/fever', method: 'POST' });
	});

	it('revokes it with a DELETE', async () => {
		const { user, last } = api([undefined]);
		await user.revokeFeverKey();
		expect(last()).toMatchObject({ path: '/me/fever', method: 'DELETE' });
	});
});

describe('logout hook', () => {
	it('runs after the local session is cleared, even when the revoke call fails', async () => {
		const recorder = recordingHttpClient();
		const store = memoryStore({ access: 'a', refresh: 'r' });
		recorder.http.request = async () => {
			throw new Error('network down');
		};
		let seenRefresh: string | null = 'unset';
		const user = createUserApi(recorder.http, store, {
			onSignedOut: () => {
				seenRefresh = store.getRefreshToken();
			}
		});

		await expect(user.logout()).rejects.toThrow('network down');
		expect(seenRefresh).toBeNull();
	});
});

describe('logout after a rotation mid-request', () => {
	it('revokes the refresh token that is current when the first attempt is refused', async () => {
		const recorder = recordingHttpClient();
		const store = memoryStore({ access: 'a', refresh: 'r1' });
		const bodies: unknown[] = [];
		recorder.http.request = async (_path: string, options?: { body?: unknown }) => {
			bodies.push(options?.body);
			if (bodies.length === 1) {
				store.setTokens({ accessToken: 'a2', refreshToken: 'r2' });
				throw new ApiError(401, {});
			}
			return undefined as never;
		};
		const user = createUserApi(recorder.http, store);

		await user.logout();

		expect(bodies).toEqual([{ refresh_token: 'r1' }, { refresh_token: 'r2' }]);
		expect(store.getRefreshToken()).toBeNull();
	});

	it('does not retry when the token did not change', async () => {
		const recorder = recordingHttpClient();
		const store = memoryStore({ access: 'a', refresh: 'r1' });
		let calls = 0;
		recorder.http.request = async () => {
			calls += 1;
			throw new ApiError(401, {});
		};
		const user = createUserApi(recorder.http, store);

		await expect(user.logout()).rejects.toBeInstanceOf(ApiError);
		expect(calls).toBe(1);
	});
});
