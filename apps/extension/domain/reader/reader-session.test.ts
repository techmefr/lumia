import { describe, expect, it } from 'vitest';
import { ApiError, createLumiaClient, type TokenStore } from '@lumia/core';
import { isSessionLost, readerSession } from './reader-session';

function clientWith(access: string | null, refresh: string | null) {
	const tokenStore: TokenStore = {
		getAccessToken: () => access,
		getRefreshToken: () => refresh,
		setTokens: () => undefined,
		setAccessToken: () => undefined,
		clear: () => undefined
	};
	return createLumiaClient('https://lumia.test/api', tokenStore);
}

describe('readerSession', () => {
	it('needs the instance address when there is no client', () => {
		expect(readerSession(null)).toBe('unconfigured');
	});

	it('needs a sign-in when the client holds no token', () => {
		expect(readerSession(clientWith(null, null))).toBe('unauthenticated');
	});

	it('is ready with either token, since a refresh token alone can renew the session', () => {
		expect(readerSession(clientWith('a', 'r'))).toBe('ready');
		expect(readerSession(clientWith(null, 'r'))).toBe('ready');
	});
});

describe('isSessionLost', () => {
	it('is true for an unauthorised answer only', () => {
		expect(isSessionLost(new ApiError(401, null))).toBe(true);
		expect(isSessionLost(new ApiError(500, null))).toBe(false);
		expect(isSessionLost(new TypeError('offline'))).toBe(false);
	});
});
