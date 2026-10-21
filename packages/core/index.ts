import { createHttpClient } from './technical/http-client';
import { createLocalStorageTokenStore, type TokenStore } from './technical/token-store';
import { createArticleApi } from './domain/article/api';
import { createFeedApi } from './domain/feed/api';
import { createHighlightApi } from './domain/highlight/api';
import { createInstanceApi } from './domain/instance/api';
import { createNewsletterApi } from './domain/newsletter/api';
import { createPlaylistApi } from './domain/playlist/api';
import { createRecommendationApi } from './domain/recommendation/api';
import { createUserApi } from './domain/user/api';

export * from './technical/http-client';
export * from './technical/token-store';
export * from './technical/sanitize-html';
export * from './domain/user/types';
export * from './domain/user/api';
export * from './domain/instance/types';
export * from './domain/instance/api';
export * from './domain/feed/types';
export * from './domain/feed/api';
export * from './domain/article/types';
export * from './domain/article/api';
export * from './domain/article/video';
export * from './domain/recommendation/types';
export * from './domain/recommendation/api';
export * from './domain/highlight/types';
export * from './domain/highlight/api';
export * from './domain/highlight/anchor';
export * from './domain/newsletter/types';
export * from './domain/newsletter/api';
export * from './domain/playlist/types';
export * from './domain/playlist/api';

export function createLumiaClient(baseUrl: string, tokenStore: TokenStore = createLocalStorageTokenStore()) {
	const http = createHttpClient({ baseUrl, tokenStore });
	return {
		tokenStore,
		user: createUserApi(http, tokenStore),
		instance: createInstanceApi(http),
		feed: createFeedApi(http),
		article: createArticleApi(http),
		newsletter: createNewsletterApi(http),
		recommendation: createRecommendationApi(http),
		playlist: createPlaylistApi(http),
		highlight: createHighlightApi(http)
	};
}

export type LumiaClient = ReturnType<typeof createLumiaClient>;
