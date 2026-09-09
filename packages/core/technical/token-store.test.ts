import { afterEach, describe, expect, it } from 'vitest';
import { createLocalStorageTokenStore } from './token-store';

const ACCESS_KEY = 'lumia.access_token';
const REFRESH_KEY = 'lumia.refresh_token';

afterEach(() => {
	localStorage.clear();
});

describe('createLocalStorageTokenStore', () => {
	it('reports no token before anything is stored', () => {
		const store = createLocalStorageTokenStore();
		expect(store.getAccessToken()).toBeNull();
		expect(store.getRefreshToken()).toBeNull();
	});

	it('reads back both tokens it was given', () => {
		const store = createLocalStorageTokenStore();
		store.setTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' });
		expect(store.getAccessToken()).toBe('access-1');
		expect(store.getRefreshToken()).toBe('refresh-1');
	});

	it('replaces only the access token on a refresh, keeping the refresh token usable', () => {
		const store = createLocalStorageTokenStore();
		store.setTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' });
		store.setAccessToken('access-2');
		expect(store.getAccessToken()).toBe('access-2');
		expect(store.getRefreshToken()).toBe('refresh-1');
	});

	it('leaves nothing behind on clear, so a logout really logs out', () => {
		const store = createLocalStorageTokenStore();
		store.setTokens({ accessToken: 'access-1', refreshToken: 'refresh-1' });
		store.clear();
		expect(localStorage.getItem(ACCESS_KEY)).toBeNull();
		expect(localStorage.getItem(REFRESH_KEY)).toBeNull();
	});

	it('survives a clear on an already empty store', () => {
		const store = createLocalStorageTokenStore();
		expect(() => store.clear()).not.toThrow();
	});

	it('shares the storage between two instances, as two tabs of the app do', () => {
		createLocalStorageTokenStore().setTokens({
			accessToken: 'access-1',
			refreshToken: 'refresh-1'
		});
		expect(createLocalStorageTokenStore().getAccessToken()).toBe('access-1');
	});
});
