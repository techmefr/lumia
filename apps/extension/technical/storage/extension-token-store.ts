import type { TokenStore } from '@lumia/core';
import type { StorageArea } from '$technical/browser/extension-api';

const ACCESS_KEY = 'lumia.access_token';
const REFRESH_KEY = 'lumia.refresh_token';
const LOCK_NAME = 'lumia-token-refresh';

function asToken(value: unknown): string | null {
	return typeof value === 'string' ? value : null;
}

function withLock<T>(task: () => Promise<T>): Promise<T> {
	const locks = typeof navigator === 'undefined' ? undefined : navigator.locks;
	return locks ? locks.request(LOCK_NAME, task) : task();
}

export async function createExtensionTokenStore(area: StorageArea): Promise<TokenStore> {
	let accessToken: string | null = null;
	let refreshToken: string | null = null;
	let writes: Promise<void> = Promise.resolve();

	async function reload(): Promise<void> {
		await writes;
		const stored = await area.get([ACCESS_KEY, REFRESH_KEY]);
		accessToken = asToken(stored[ACCESS_KEY]);
		refreshToken = asToken(stored[REFRESH_KEY]);
	}

	let pending = 0;

	function enqueue(write: () => Promise<void>): void {
		const settle = () => {
			pending -= 1;
		};
		const run = pending === 0 ? write() : writes.then(write);
		pending += 1;
		writes = run.then(settle, settle).then(() => undefined);
	}

	await reload();

	area.onChanged?.addListener((changes) => {
		if (ACCESS_KEY in changes) accessToken = asToken(changes[ACCESS_KEY].newValue);
		if (REFRESH_KEY in changes) refreshToken = asToken(changes[REFRESH_KEY].newValue);
	});

	return {
		getAccessToken: () => accessToken,
		getRefreshToken: () => refreshToken,
		setTokens(tokens) {
			accessToken = tokens.accessToken;
			refreshToken = tokens.refreshToken;
			const items = { [ACCESS_KEY]: tokens.accessToken, [REFRESH_KEY]: tokens.refreshToken };
			enqueue(() => area.set(items));
		},
		setAccessToken(token) {
			accessToken = token;
			enqueue(() => area.set({ [ACCESS_KEY]: token }));
		},
		clear() {
			accessToken = null;
			refreshToken = null;
			enqueue(() => area.remove([ACCESS_KEY, REFRESH_KEY]));
		},
		settled: () => writes,
		reload,
		exclusive: withLock
	};
}
