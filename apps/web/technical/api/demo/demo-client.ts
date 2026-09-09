import type {
	ArticleDetail,
	ArticleSummary,
	DiscoverSuggestion,
	Feed,
	FeedUpdate,
	FeedbackUpdate,
	FilterMode,
	FilterRule,
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
	SEED_DISCOVER,
	SEED_DISLIKED,
	SEED_FAVORITES,
	SEED_FEEDS,
	SEED_FOLDERS,
	SEED_LIKED,
	SEED_PLAYLISTS,
	SEED_READ,
	SEED_SAVED,
	type SeedArticle
} from './seed';

const STORAGE_KEY = 'lumia:demo-state';
const WORDS_PER_MINUTE = 200;
/** Enough delay for skeletons and pending states to be visible, short enough not to annoy. */
const LATENCY_MS = 180;
/** Same numbers as the backend, so the demo teaches the right feel for a vote. */
const VOTE_DELTA: Record<'like' | 'dislike', number> = { like: 1.5, dislike: -0.5 };
const BOOST_WEIGHT = 1;
const TANH_SCALE = 3;

interface Feedback {
	sentiment: 'like' | 'dislike' | null;
	saved: boolean;
	favorite: boolean;
	read: boolean;
	scroll_progress: number;
}

/** The four score tables the backend keeps, flattened to plain records. */
interface Scores {
	keywords: Record<string, number>;
	feeds: Record<string, number>;
	authors: Record<string, number>;
	categories: Record<string, number>;
}

interface DemoState {
	folders: Folder[];
	feeds: Feed[];
	articleIds: string[];
	feedback: Record<string, Feedback>;
	playlists: { id: string; name: string; article_ids: string[] }[];
	filterRules: FilterRule[];
	scores: Scores;
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

function emptyScores(): Scores {
	return { keywords: {}, feeds: {}, authors: {}, categories: {} };
}

/**
 * Spreads one vote over every dimension of an article, exactly as the backend's feedback service
 * does: the demo has to teach the right feel for what a like changes.
 */
function accumulate(scores: Scores, article: SeedArticle, delta: number): void {
	for (const term of article.keywords) {
		scores.keywords[term] = (scores.keywords[term] ?? 0) + delta;
	}
	scores.feeds[article.feed_id] = (scores.feeds[article.feed_id] ?? 0) + delta;
	if (article.author_name) {
		scores.authors[article.author_name] = (scores.authors[article.author_name] ?? 0) + delta;
	}
	if (article.category_name) {
		scores.categories[article.category_name] =
			(scores.categories[article.category_name] ?? 0) + delta;
	}
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
	const scores = emptyScores();
	for (const [ids, sentiment] of [
		[SEED_LIKED, 'like'],
		[SEED_DISLIKED, 'dislike']
	] as const) {
		for (const id of ids) {
			const article = SEED_ARTICLES.find((candidate) => candidate.id === id);
			if (!article) continue;
			feedback[id].sentiment = sentiment;
			accumulate(scores, article, VOTE_DELTA[sentiment]);
		}
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
		filterRules: [],
		scores,
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

	function ruleTerms(mode: FilterMode): string[] {
		return state.filterRules.filter((rule) => rule.mode === mode).map((rule) => rule.term);
	}

	/**
	 * Same substring match as the backend: title and summary only, never the rendered HTML, where a
	 * term like « img » would match markup instead of subject matter.
	 */
	function matchesTerms(article: SeedArticle, terms: string[]): boolean {
		if (terms.length === 0) return false;
		const haystack = `${article.title} ${article.summary}`.toLowerCase();
		return terms.some((term) => haystack.includes(term));
	}

	/** Average affinity over the article's dimensions, boost rules included. */
	function rawScore(article: SeedArticle): number {
		const parts = article.keywords.map((term) => state.scores.keywords[term] ?? 0);
		parts.push(state.scores.feeds[article.feed_id] ?? 0);
		if (article.author_name) parts.push(state.scores.authors[article.author_name] ?? 0);
		if (article.category_name) parts.push(state.scores.categories[article.category_name] ?? 0);
		let average = parts.length ? parts.reduce((total, part) => total + part, 0) / parts.length : 0;
		if (matchesTerms(article, ruleTerms('boost'))) average += BOOST_WEIGHT;
		return average;
	}

	function toRelevance(raw: number): number {
		return Math.round(50 + 50 * Math.tanh(raw / TANH_SCALE));
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
			relevance_score: toRelevance(rawScore(article)),
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

	/**
	 * Namespaced away from the seed on purpose. The counter starts at 1, so a plain
	 * `article-${n}` collided with the seed's own `article-1`..`article-12`: saving a url handed
	 * back the seed article of that number instead of the page just saved, because `seedArticle`
	 * looks in the seed first. A prefix the seed can never use makes that impossible again.
	 */
	function nextId(prefix: string): string {
		state.nextId += 1;
		return `demo-${prefix}-${state.nextId}`;
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
			importOpml: async () => settle(state.feeds.map((feed) => ({ ...feed }))),
			discoverFeeds: async (limit = 6) => {
				const subscribed = new Set(state.feeds.map((feed) => feed.url.replace(/\/$/, '')));
				// Only positive interest counts, as on the backend: a dislike says nothing about a source
				// that merely mentions the topic.
				const affinities: Record<string, number> = {};
				for (const [term, score] of Object.entries(state.scores.keywords)) {
					if (score > 0) affinities[term.toLowerCase()] = score;
				}
				for (const [name, score] of Object.entries(state.scores.categories)) {
					if (score > 0) {
						affinities[name.toLowerCase()] = Math.max(affinities[name.toLowerCase()] ?? 0, score);
					}
				}
				const ranked: DiscoverSuggestion[] = SEED_DISCOVER.filter(
					(entry) => !subscribed.has(entry.url.replace(/\/$/, ''))
				)
					.map((entry) => ({
						...entry,
						topics: [...entry.topics],
						affinity: entry.topics.reduce((total, topic) => total + (affinities[topic] ?? 0), 0)
					}))
					.sort((left, right) => (right.affinity ?? 0) - (left.affinity ?? 0));
				return settle(ranked.slice(0, limit));
			}
		},
		article: {
			listArticles: async (params: ListArticlesParams = {}) => {
				const muted = ruleTerms('mute');
				let ids = sortedIds().filter((id) => {
					if (!matches(id, params)) return false;
					const article = seedArticle(id);
					return article !== undefined && !matchesTerms(article, muted);
				});
				if (params.sort === 'relevance') {
					// Recency stays the tie-breaker, so an untouched library still reads chronologically.
					ids = ids.sort((left, right) => {
						const a = seedArticle(left);
						const b = seedArticle(right);
						if (!a || !b) return 0;
						return rawScore(b) - rawScore(a);
					});
				}
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
				if (update.sentiment !== undefined && update.sentiment !== feedback.sentiment) {
					// The previous vote is undone before the new one is applied, exactly as the backend
					// does, so flipping like → dislike doesn't leave the old boost behind.
					const article = seedArticle(articleId);
					if (article) {
						if (feedback.sentiment) accumulate(state.scores, article, -VOTE_DELTA[feedback.sentiment]);
						if (update.sentiment) accumulate(state.scores, article, VOTE_DELTA[update.sentiment]);
					}
					feedback.sentiment = update.sentiment;
				}
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
			},
			listFilterRules: async () => settle(state.filterRules.map((rule) => ({ ...rule }))),
			addFilterRule: async (term: string, mode: FilterMode) => {
				const normalized = term.trim().toLowerCase();
				// Idempotent like the backend: the same term in the same mode returns the existing rule.
				const existing = state.filterRules.find(
					(rule) => rule.term === normalized && rule.mode === mode
				);
				if (existing) return settle({ ...existing });
				const rule: FilterRule = { id: nextId('rule'), term: normalized, mode };
				state.filterRules = [...state.filterRules, rule];
				persist();
				return settle({ ...rule });
			},
			deleteFilterRule: async (ruleId: string) => {
				state.filterRules = state.filterRules.filter((rule) => rule.id !== ruleId);
				persist();
				return settle(undefined);
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
			createPlaylistForDuration: async (targetMinutes: number) => {
				const muted = ruleTerms('mute');
				const candidates = sortedIds()
					.map((id) => ({ id, article: seedArticle(id) }))
					.filter(
						(entry): entry is { id: string; article: SeedArticle } =>
							entry.article !== undefined &&
							!feedbackFor(entry.id).read &&
							!matchesTerms(entry.article, muted)
					)
					.sort((left, right) => rawScore(right.article) - rawScore(left.article));

				// Greedy over the relevance order, like the backend: reading-time estimates are
				// approximate, so squeezing the last minute out would be false precision.
				const chosen: string[] = [];
				let remaining = targetMinutes;
				for (const entry of candidates) {
					const minutes = readingMinutes(entry.article.paragraphs);
					if (minutes > remaining) continue;
					chosen.push(entry.id);
					remaining -= minutes;
					if (remaining <= 0) break;
				}

				const stamp = new Date();
				const day = String(stamp.getDate()).padStart(2, '0');
				const month = String(stamp.getMonth() + 1).padStart(2, '0');
				const playlist = {
					id: nextId('playlist'),
					name: `${targetMinutes} min · ${day}/${month}`,
					article_ids: chosen
				};
				state.playlists = [...state.playlists, playlist];
				persist();
				return settle(playlistDetail(playlist.id));
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
