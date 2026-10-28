import { ApiError, type LumiaClient } from '@lumia/core';

export type ReaderSession = 'ready' | 'unconfigured' | 'unauthenticated';

export function readerSession(client: LumiaClient | null): ReaderSession {
	if (client === null) return 'unconfigured';
	const { tokenStore } = client;
	const signedIn = tokenStore.getAccessToken() !== null || tokenStore.getRefreshToken() !== null;
	return signedIn ? 'ready' : 'unauthenticated';
}

export function isSessionLost(error: unknown): boolean {
	return error instanceof ApiError && error.status === 401;
}
