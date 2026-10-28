import { ApiError, type LumiaClient } from '@lumia/core';

export type SaveOutcome =
	| 'saved'
	| 'already_saved'
	| 'unsupported'
	| 'unconfigured'
	| 'unauthenticated'
	| 'failed';

function isWebAddress(url: string | undefined): url is string {
	if (url === undefined) return false;
	try {
		const { protocol } = new URL(url);
		return protocol === 'http:' || protocol === 'https:';
	} catch {
		return false;
	}
}

export async function savePage(
	client: LumiaClient | null,
	url: string | undefined
): Promise<SaveOutcome> {
	if (!isWebAddress(url)) return 'unsupported';
	if (client === null) return 'unconfigured';
	const { tokenStore } = client;
	if (tokenStore.getAccessToken() === null && tokenStore.getRefreshToken() === null) {
		return 'unauthenticated';
	}
	try {
		const article = await client.article.saveUrl(url);
		return article.already_saved ? 'already_saved' : 'saved';
	} catch (error) {
		return error instanceof ApiError && error.status === 401 ? 'unauthenticated' : 'failed';
	}
}
