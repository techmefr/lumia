import type { TokenStore } from '@lumia/core';
import type { StorageArea } from '$technical/browser/extension-api';

const ACCESS_KEY = 'lumia.access_token';
const REFRESH_KEY = 'lumia.refresh_token';

function asToken(value: unknown): string | null {
	return typeof value === 'string' ? value : null;
}

export async function createExtensionTokenStore(area: StorageArea): Promise<TokenStore> {
	const stored = await area.get([ACCESS_KEY, REFRESH_KEY]);
	let accessToken = asToken(stored[ACCESS_KEY]);
	let refreshToken = asToken(stored[REFRESH_KEY]);

	return {
		getAccessToken: () => accessToken,
		getRefreshToken: () => refreshToken,
		setTokens(tokens) {
			accessToken = tokens.accessToken;
			refreshToken = tokens.refreshToken;
			void area.set({ [ACCESS_KEY]: accessToken, [REFRESH_KEY]: refreshToken });
		},
		setAccessToken(token) {
			accessToken = token;
			void area.set({ [ACCESS_KEY]: token });
		},
		clear() {
			accessToken = null;
			refreshToken = null;
			void area.remove([ACCESS_KEY, REFRESH_KEY]);
		}
	};
}
