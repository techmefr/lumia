export interface TokenStore {
	getAccessToken(): string | null;
	getRefreshToken(): string | null;
	setTokens(tokens: { accessToken: string; refreshToken: string }): void;
	setAccessToken(accessToken: string): void;
	clear(): void;
}

const ACCESS_KEY = 'lumia.access_token';
const REFRESH_KEY = 'lumia.refresh_token';

export function createLocalStorageTokenStore(): TokenStore {
	return {
		getAccessToken() {
			return localStorage.getItem(ACCESS_KEY);
		},
		getRefreshToken() {
			return localStorage.getItem(REFRESH_KEY);
		},
		setTokens({ accessToken, refreshToken }) {
			localStorage.setItem(ACCESS_KEY, accessToken);
			localStorage.setItem(REFRESH_KEY, refreshToken);
		},
		setAccessToken(accessToken) {
			localStorage.setItem(ACCESS_KEY, accessToken);
		},
		clear() {
			localStorage.removeItem(ACCESS_KEY);
			localStorage.removeItem(REFRESH_KEY);
		}
	};
}
