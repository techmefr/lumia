import { createHttpClient } from './technical/http-client';
import { createLocalStorageTokenStore, type TokenStore } from './technical/token-store';
import { createArticleApi } from './domain/article/api';
import { createFeedApi } from './domain/feed/api';
import { createRecommendationApi } from './domain/recommendation/api';
import { createUserApi } from './domain/user/api';

export * from './technical/http-client';
export * from './technical/token-store';
export * from './technical/sanitize-html';
export * from './domain/user/types';
export * from './domain/user/api';
export * from './domain/feed/types';
export * from './domain/feed/api';
export * from './domain/article/types';
export * from './domain/article/api';
export * from './domain/recommendation/types';
export * from './domain/recommendation/api';

export function createLumiaClient(baseUrl: string, tokenStore: TokenStore = createLocalStorageTokenStore()) {
	const http = createHttpClient({ baseUrl, tokenStore });
	return {
		tokenStore,
		user: createUserApi(http, tokenStore),
		feed: createFeedApi(http),
		article: createArticleApi(http),
		recommendation: createRecommendationApi(http)
	};
}

export type LumiaClient = ReturnType<typeof createLumiaClient>;
