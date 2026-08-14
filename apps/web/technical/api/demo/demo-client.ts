import type {
	ArticleDetail,
	ArticleSummary,
	Feed,
	FeedUpdate,
	FeedbackUpdate,
	Folder,
	ListArticlesParams,
	LumiaClient,
	MarkReadScope,
	Me,
	MeUpdate,
	PlaylistDetail,
	PlaylistSummary,
	TokenStore,
	UnreadCounts
} from '@lumia/core';
import {
	SEED_ARTICLES,
	SEED_FAVORITES,
	SEED_FEEDS,
	SEED_FOLDERS,
	SEED_PLAYLISTS,
	SEED_READ,
	SEED_SAVED,
	type SeedArticle
} from './seed';

const STORAGE_KEY = 'lumia:demo-state';
const WORDS_PER_MINUTE = 200;
/** Enough delay for skeletons and pending states to be visible, short enough not to annoy. */
const LATENCY_MS = 180;

interface Feedback {
	sentiment: 'like' | 'dislike' | null;
	saved: boolean;
	favorite: boolean;
	read: boolean;
	scroll_progress: number;
}

interface DemoState {
	folders: Folder[];
	feeds: Feed[];
	articleIds: string[];
	feedback: Record<string, Feedback>;
	playlists: { id: string; name: string; article_ids: string[] }[];
	me: Me;
	nextId: number;
}

function emptyFeedback(): Feedback {
	return { sentiment: null, saved: false, favorite: false, read: false, scroll_progress: 0 };
}

function readingMinutes(paragraphs: string[]): number {
	const words = paragraphs.join(' ').split(/\s+/).filter(Boolean).length;
	return Math.max(1, Math.round(words / WORDS_PER_MINUTE));
}

function initialState(): DemoState {
	const feedback: Record<string, Feedback> = {};
	for (const article of SEED_ARTICLES) feedback[article.id] = emptyFeedback();
	for (const id of SEED_SAVED) feedback[id].saved = true;
	for (const id of SEED_FAVORITES) feedback[id].favorite = true;
	for (const id of SEED_READ) {
		feedback[id].read = true;
		feedback[id].scroll_progress = 1;
	}
	return {
		folders: SEED_FOLDERS.map((folder) => ({ ...folder })),
		feeds: SEED_FEEDS.map((feed) => ({
			id: feed.id,
			folder_id: feed.folder_id,
			source_type: 'miniflux',
			external_feed_id: feed.id,
			title: feed.title,
			url: feed.url
		})),
		articleIds: SEED_ARTICLES.map((article) => article.id),
		feedback,
		playlists: SEED_PLAYLISTS.map((playlist) => ({ ...playlist, article_ids: [...playlist.article_ids] })),
		me: {
			id: 'demo-user',
			email: 'demo@lumia.local',
			username: 'Démo',
			role: 'admin',
			theme: 'system',
			orbit_position: 'right',
			font_base_size: 16,
			preferred_language: 'fr',
			ai_provider: null,
			ai_endpoint_url: null,
			ai_model: null,
			ai_api_key_set: false,
			translation_provider: null,
			translation_api_key_set: false
		},
		nextId: 1
	};
}

/**
 * Articles added during the demo session (a saved url). Kept apart from the seed so the seed
 * stays a pure constant.
 */
const runtimeArticles = new Map<string, SeedArticle>();

function seedArticle(id: string): SeedArticle | undefined {
	return SEED_ARTICLES.find((article) => article.id === id) ?? runtimeArticles.get(id);
}

export function createDemoClient(): LumiaClient {
	let state = load();

	function load(): DemoState {
		try {
			const stored = localStorage.getItem(STORAGE_KEY);
			if (stored) return { ...initialState(), ...(JSON.parse(stored) as DemoState) };
		} catch {
			/* a corrupt or unavailable store just means a fresh demo */
		}
		return initialState();
	}

	function persist(): void {
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
		} catch {
			/* private browsing: the demo still works, it just won't survive a reload */
		}
	}

	async function settle<T>(value: T): Promise<T> {
		await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
		return value;
	}

	function feedbackFor(articleId: string): Feedback {
		state.feedback[articleId] ??= emptyFeedback();
		return state.feedback[articleId];
	}

	function toSummary(id: string): ArticleSummary | null {
		const article = seedArticle(id);
		if (!article) return null;
		const feed = state.feeds.find((candidate) => candidate.id === article.feed_id);
		const state_ = feedbackFor(id);
		return {
			id: article.id,
			feed_id: article.feed_id,
			author_id: article.author_name ? `author-${article.author_name}` : null,
			author_name: article.author_name,
			category_id: article.category_name ? `category-${article.category_name}` : null,
			category_name: article.category_name,
			source_label: feed?.title ?? 'Source inconnue',
			title: article.title,
			url: `https://exemple.test/${article.id}`,
			summary: article.summary,
			image_url: null,
			published_at: article.published_at,
			reading_minutes: readingMinutes(article.paragraphs),
			read: state_.read,
			scroll_progress: state_.scroll_progress
		};
	}

	function summaries(ids: string[]): ArticleSummary[] {
		return ids.map(toSummary).filter((article): article is ArticleSummary => article !== null);
	}

	function sortedIds(): string[] {
		return [...state.articleIds].sort((left, right) => {
			const a = seedArticle(left)?.published_at ?? '';
			const b = seedArticle(right)?.published_at ?? '';
			return b.localeCompare(a);
		});
	}

	function matches(id: string, params: ListArticlesParams): boolean {
		const article = seedArticle(id);
		if (!article) return false;
		const feed = state.feeds.find((candidate) => candidate.id === article.feed_id);
		if (params.feedId && article.feed_id !== params.feedId) return false;
		if (params.folderId && feed?.folder_id !== params.folderId) return false;
		if (params.authorId && `author-${article.author_name}` !== params.authorId) return false;
		if (params.categoryId && `category-${article.category_name}` !== params.categoryId) return false;
		if (params.keywordId && !article.keywords.includes(params.keywordId.replace('keyword-', ''))) {
			return false;
		}
		if (params.unreadOnly && feedbackFor(id).read) return false;
		if (params.query) {
			const haystack = [article.title, article.summary, ...article.paragraphs]
				.join(' ')
				.toLowerCase();
			if (!haystack.includes(params.query.toLowerCase())) return false;
		}
		return true;
	}

	function page(ids: string[], limit = 20, offset = 0): string[] {
		return ids.slice(offset, offset + limit);
	}

	function playlistDetail(playlistId: string): PlaylistDetail {
		const playlist = state.playlists.find((candidate) => candidate.id === playlistId);
		if (!playlist) throw new Error('playlist introuvable');
		return { id: playlist.id, name: playlist.name, articles: summaries(playlist.article_ids) };
	}

	function playlistSummary(playlist: DemoState['playlists'][number]): PlaylistSummary {
		const articles = summaries(playlist.article_ids);
		return {
			id: playlist.id,
			name: playlist.name,
			item_count: articles.length,
			total_reading_minutes: articles.reduce((total, article) => total + article.reading_minutes, 0)
		};
	}

	function nextId(prefix: string): string {
		state.nextId += 1;
		return `${prefix}-${state.nextId}`;
	}

	// The demo has no login, so the token store answers as if a session were open: the route
	// guards stay untouched and behave exactly as they do against a real backend.
	const tokenStore: TokenStore = {
		getAccessToken: () => 'demo',
		getRefreshToken: () => 'demo',
		setTokens: () => {},
		setAccessToken: () => {},
		clear: () => {}
	};

	return {
		tokenStore,
		user: {
			onboardAdmin: async () => settle(undefined),
			login: async () => settle(undefined),
			logout: async () => {
				state = initialState();
				persist();
				return settle(undefined);
			},
			requestMagicLink: async () => settle(undefined),
			verifyMagicLink: async () => settle(undefined),
			getMe: async () => settle({ ...state.me }),
			updateMe: async (payload: MeUpdate) => {
				const { ai_api_key, translation_api_key, ...rest } = payload;
				state.me = { ...state.me, ...rest } as Me;
				if (ai_api_key !== undefined) state.me.ai_api_key_set = Boolean(ai_api_key);
				if (translation_api_key !== undefined) {
					state.me.translation_api_key_set = Boolean(translation_api_key);
				}
				persist();
				return settle({ ...state.me });
			},
			isAuthenticated: () => true
		},
		feed: {
			listFolders: async () => settle(state.folders.map((folder) => ({ ...folder }))),
			createFolder: async (name: string) => {
				const folder = { id: nextId('folder'), name };
				state.folders = [...state.folders, folder];
				persist();
				return settle({ ...folder });
			},
			renameFolder: async (folderId: string, name: string) => {
				const folder = state.folders.find((candidate) => candidate.id === folderId);
				if (!folder) throw new Error('dossier introuvable');
				folder.name = name;
				persist();
				return settle({ ...folder });
			},
			deleteFolder: async (folderId: string) => {
				state.folders = state.folders.filter((folder) => folder.id !== folderId);
				// Same rule as the backend: deleting a folder unfiles its feeds, it never takes them.
				for (const feed of state.feeds) if (feed.folder_id === folderId) feed.folder_id = null;
				persist();
				return settle(undefined);
			},
			listFeeds: async () => settle(state.feeds.map((feed) => ({ ...feed }))),
			updateFeed: async (feedId: string, update: FeedUpdate) => {
				const feed = state.feeds.find((candidate) => candidate.id === feedId);
				if (!feed) throw new Error('flux introuvable');
				if (update.title !== undefined) feed.title = update.title;
				if ('folder_id' in update) feed.folder_id = update.folder_id ?? null;
				persist();
				return settle({ ...feed });
			},
			deleteFeed: async (feedId: string) => {
				state.feeds = state.feeds.filter((feed) => feed.id !== feedId);
				state.articleIds = state.articleIds.filter((id) => seedArticle(id)?.feed_id !== feedId);
				persist();
				return settle(undefined);
			},
			getUnreadCounts: async () => {
				const counts: UnreadCounts = { total: 0, feeds: {}, folders: {} };
				for (const id of state.articleIds) {
					if (feedbackFor(id).read) continue;
					const article = seedArticle(id);
					if (!article) continue;
					const feed = state.feeds.find((candidate) => candidate.id === article.feed_id);
					if (!feed) continue;
					counts.total += 1;
					counts.feeds[feed.id] = (counts.feeds[feed.id] ?? 0) + 1;
					if (feed.folder_id) {
						counts.folders[feed.folder_id] = (counts.folders[feed.folder_id] ?? 0) + 1;
					}
				}
				return settle(counts);
			},
			addFeedByUrl: async (url: string, folderId?: string | null) => {
				const feed: Feed = {
					id: nextId('feed'),
					folder_id: folderId ?? null,
					source_type: 'miniflux',
					external_feed_id: nextId('external'),
					title: new URL(url).hostname.replace(/^www\./, ''),
					url
				};
				state.feeds = [...state.feeds, feed];
				persist();
				return settle({ ...feed });
			},
			importOpml: async () => settle(state.feeds.map((feed) => ({ ...feed })))
		},
		article: {
			listArticles: async (params: ListArticlesParams = {}) => {
				const ids = sortedIds().filter((id) => matches(id, params));
				return settle(summaries(page(ids, params.limit, params.offset)));
			},
			getArticle: async (articleId: string) => {
				const article = seedArticle(articleId);
				const summary = toSummary(articleId);
				if (!article || !summary) throw new Error('article introuvable');
				const detail: ArticleDetail = {
					...summary,
					content: article.paragraphs.map((paragraph) => `<p>${paragraph}</p>`).join(''),
					keywords: article.keywords.map((term) => ({ id: `keyword-${term}`, term }))
				};
				return settle(detail);
			},
			saveUrl: async (url: string) => {
				const id = nextId('article');
				const host = new URL(url).hostname.replace(/^www\./, '');
				runtimeArticles.set(id, {
					id,
					feed_id: state.feeds[0]?.id ?? 'feed-fibre',
					author_name: host,
					category_name: 'Enregistrés',
					title: `Page enregistrée depuis ${host}`,
					summary: "Enregistrée pendant la démo : dans la vraie app, la page est téléchargée puis nettoyée.",
					keywords: ['enregistré'],
					published_at: new Date().toISOString(),
					image_hue: 265,
					paragraphs: [
						`Cette page vient de ${url}. La démo ne va pas la chercher : elle tourne entièrement dans le navigateur, sans serveur ni accès réseau vers des sites tiers.`,
						"Sur une instance réelle, Lumia télécharge la page, en retire le décor du site avec trafilatura, en extrait les mots-clés et un résumé, puis la range dans un flux « Enregistrés » propre à ton compte."
					]
				});
				state.articleIds = [id, ...state.articleIds];
				state.feedback[id] = emptyFeedback();
				state.feedback[id].saved = true;
				persist();
				const summary = toSummary(id);
				if (!summary) throw new Error('article introuvable');
				return settle(summary);
			}
		},
		recommendation: {
			getEtincelle: async (limit = 20, offset = 0) => {
				const ids = sortedIds().filter((id) => {
					const feedback = feedbackFor(id);
					return !feedback.read && feedback.sentiment === null;
				});
				return settle(summaries(page(ids, limit, offset)));
			},
			getSaved: async (limit = 20, offset = 0) => {
				const ids = sortedIds().filter((id) => feedbackFor(id).saved);
				return settle(summaries(page(ids, limit, offset)));
			},
			getFavorites: async (limit = 20, offset = 0) => {
				const ids = sortedIds().filter((id) => feedbackFor(id).favorite);
				return settle(summaries(page(ids, limit, offset)));
			},
			sendFeedback: async (articleId: string, update: FeedbackUpdate) => {
				const feedback = feedbackFor(articleId);
				if (update.sentiment !== undefined) feedback.sentiment = update.sentiment;
				if (update.saved !== undefined) feedback.saved = update.saved;
				if (update.favorite !== undefined) feedback.favorite = update.favorite;
				if (update.read !== undefined) feedback.read = update.read;
				if (update.scroll_progress !== undefined) {
					// Same rule as the backend: the stored position never rewinds.
					feedback.scroll_progress = Math.max(feedback.scroll_progress, update.scroll_progress);
				}
				persist();
				return settle(undefined);
			},
			markRead: async (scope: MarkReadScope) => {
				const read = scope.read ?? true;
				let ids: string[] = [];
				if (scope.article_ids) ids = scope.article_ids;
				else if (scope.feed_id) {
					ids = state.articleIds.filter((id) => seedArticle(id)?.feed_id === scope.feed_id);
				} else if (scope.folder_id) {
					const feedIds = state.feeds
						.filter((feed) => feed.folder_id === scope.folder_id)
						.map((feed) => feed.id);
					ids = state.articleIds.filter((id) => {
						const feedId = seedArticle(id)?.feed_id;
						return feedId !== undefined && feedIds.includes(feedId);
					});
				}
				let updated = 0;
				for (const id of ids) {
					const feedback = feedbackFor(id);
					if (feedback.read === read) continue;
					feedback.read = read;
					updated += 1;
				}
				persist();
				return settle({ updated });
			}
		},
		playlist: {
			listPlaylists: async () => settle(state.playlists.map(playlistSummary)),
			createPlaylist: async (name: string) => {
				const playlist = { id: nextId('playlist'), name, article_ids: [] };
				state.playlists = [...state.playlists, playlist];
				persist();
				return settle(playlistSummary(playlist));
			},
			getPlaylist: async (playlistId: string) => settle(playlistDetail(playlistId)),
			renamePlaylist: async (playlistId: string, name: string) => {
				const playlist = state.playlists.find((candidate) => candidate.id === playlistId);
				if (!playlist) throw new Error('playlist introuvable');
				playlist.name = name;
				persist();
				return settle(playlistSummary(playlist));
			},
			deletePlaylist: async (playlistId: string) => {
				state.playlists = state.playlists.filter((playlist) => playlist.id !== playlistId);
				persist();
				return settle(undefined);
			},
			addArticle: async (playlistId: string, articleId: string) => {
				const playlist = state.playlists.find((candidate) => candidate.id === playlistId);
				if (!playlist) throw new Error('playlist introuvable');
				if (!playlist.article_ids.includes(articleId)) playlist.article_ids.push(articleId);
				persist();
				return settle(playlistDetail(playlistId));
			},
			removeArticle: async (playlistId: string, articleId: string) => {
				const playlist = state.playlists.find((candidate) => candidate.id === playlistId);
				if (!playlist) throw new Error('playlist introuvable');
				playlist.article_ids = playlist.article_ids.filter((id) => id !== articleId);
				persist();
				return settle(playlistDetail(playlistId));
			},
			reorder: async (playlistId: string, articleIds: string[]) => {
				const playlist = state.playlists.find((candidate) => candidate.id === playlistId);
				if (!playlist) throw new Error('playlist introuvable');
				// Ids missing from the payload stay at the end, so a stale client can't drop items.
				const missing = playlist.article_ids.filter((id) => !articleIds.includes(id));
				playlist.article_ids = [...articleIds.filter((id) => playlist.article_ids.includes(id)), ...missing];
				persist();
				return settle(playlistDetail(playlistId));
			}
		}
	};
}

/** Wipes the demo state so the seeded library comes back exactly as it started. */
export function resetDemo(): void {
	try {
		localStorage.removeItem(STORAGE_KEY);
	} catch {
		/* nothing to clear */
	}
}
