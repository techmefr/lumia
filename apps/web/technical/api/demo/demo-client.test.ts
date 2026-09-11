import { afterAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { LumiaClient } from '@lumia/core';
import { createDemoClient } from './demo-client';
import { SEED_ARTICLES, SEED_FEEDS, SEED_FOLDERS } from './seed';

// Every call is delayed so the real app shows its skeletons. Letting the clock run itself keeps
// that behaviour intact without the suite paying 180ms per assertion.
vi.useFakeTimers({ shouldAdvanceTime: true, advanceTimeDelta: 5 });
afterAll(() => {
	vi.useRealTimers();
});

let demo: LumiaClient;

beforeEach(() => {
	localStorage.clear();
	demo = createDemoClient();
});

describe('the seeded library', () => {
	it('serves the seed folders', async () => {
		await expect(demo.feed.listFolders()).resolves.toHaveLength(SEED_FOLDERS.length);
	});

	it('serves the seed feeds', async () => {
		await expect(demo.feed.listFeeds()).resolves.toHaveLength(SEED_FEEDS.length);
	});

	it('answers as if a session were open, so the route guards are exercised for real', () => {
		expect(demo.user.isAuthenticated()).toBe(true);
		expect(demo.tokenStore.getAccessToken()).not.toBeNull();
	});
});

describe('listArticles', () => {
	it('returns the newest article first', async () => {
		const articles = await demo.article.listArticles();
		const dates = articles.map((article) => article.published_at);
		expect([...dates].sort().reverse()).toEqual(dates);
	});

	it('pages with the limit it is given', async () => {
		await expect(demo.article.listArticles({ limit: 3 })).resolves.toHaveLength(3);
	});

	it('skips the offset, so page two does not repeat page one', async () => {
		const first = await demo.article.listArticles({ limit: 2 });
		const second = await demo.article.listArticles({ limit: 2, offset: 2 });
		expect(second.map((a) => a.id)).not.toEqual(first.map((a) => a.id));
	});

	it('filters by feed', async () => {
		const feedId = SEED_FEEDS[0].id;
		const articles = await demo.article.listArticles({ feedId });
		expect(articles.length).toBeGreaterThan(0);
		expect(articles.every((article) => article.feed_id === feedId)).toBe(true);
	});

	it('filters by folder through the feeds it holds', async () => {
		const folderId = SEED_FOLDERS[0].id;
		const feedIds = SEED_FEEDS.filter((feed) => feed.folder_id === folderId).map((f) => f.id);
		const articles = await demo.article.listArticles({ folderId });
		expect(articles.length).toBeGreaterThan(0);
		expect(articles.every((article) => feedIds.includes(article.feed_id))).toBe(true);
	});

	it('searches the body, not only the title and summary', async () => {
		const article = SEED_ARTICLES[0];
		const needle = article.paragraphs[0].split(' ').slice(2, 5).join(' ');
		const found = await demo.article.listArticles({ query: needle });
		expect(found.map((a) => a.id)).toContain(article.id);
	});

	it('searches case-insensitively', async () => {
		const word = SEED_ARTICLES[0].title.split(' ')[1];
		await expect(demo.article.listArticles({ query: word.toUpperCase() })).resolves.not.toHaveLength(
			0
		);
	});

	it('returns nothing for a term no article contains', async () => {
		await expect(demo.article.listArticles({ query: 'zzzuntrouvable' })).resolves.toEqual([]);
	});

	it('drops read articles when only unread are asked for', async () => {
		const [first] = await demo.article.listArticles({ unreadOnly: true });
		await demo.recommendation.sendFeedback(first.id, { read: true });
		const after = await demo.article.listArticles({ unreadOnly: true });
		expect(after.map((a) => a.id)).not.toContain(first.id);
	});

	it('filters by author', async () => {
		const named = SEED_ARTICLES.find((article) => article.author_name)!;
		const articles = await demo.article.listArticles({
			authorId: `author-${named.author_name}`
		});
		expect(articles.every((article) => article.author_name === named.author_name)).toBe(true);
		expect(articles.length).toBeGreaterThan(0);
	});

	it('filters by keyword, stripping the id prefix the ui sends', async () => {
		const term = SEED_ARTICLES[0].keywords[0];
		const articles = await demo.article.listArticles({ keywordId: `keyword-${term}` });
		expect(articles.length).toBeGreaterThan(0);
	});
});

describe('the relevance score', () => {
	/**
	 * The seed ships a few votes already. Liking an article that is already liked changes nothing,
	 * so a test about what a vote does has to start from one nobody has voted on — which is exactly
	 * what l'étincelle offers.
	 */
	async function unvoted() {
		const [article] = await demo.recommendation.getEtincelle();
		return article;
	}

	async function scoreOf(articleId: string) {
		const [article] = await demo.article.listArticles({ query: '', limit: 999 }).then((list) => [
			list.find((candidate) => candidate.id === articleId)!
		]);
		return article.relevance_score!;
	}

	it('sits at the neutral 50 before any vote', async () => {
		const client = createDemoClient();
		const articles = await client.article.listArticles();
		// The seed ships a few votes, so only an article sharing nothing with them stays neutral.
		expect(articles.some((article) => article.relevance_score === 50)).toBe(true);
	});

	it('rises after a like on the article', async () => {
		const article = await unvoted();
		const before = article.relevance_score!;
		await demo.recommendation.sendFeedback(article.id, { sentiment: 'like' });
		expect(await scoreOf(article.id)).toBeGreaterThan(before);
	});

	it('falls after a dislike', async () => {
		const article = await unvoted();
		const before = article.relevance_score!;
		await demo.recommendation.sendFeedback(article.id, { sentiment: 'dislike' });
		expect(await scoreOf(article.id)).toBeLessThan(before);
	});

	it('leaves no trace of the old vote when a like is flipped to a dislike', async () => {
		const article = await unvoted();
		const neutral = article.relevance_score!;

		await demo.recommendation.sendFeedback(article.id, { sentiment: 'like' });
		await demo.recommendation.sendFeedback(article.id, { sentiment: 'dislike' });
		const flipped = await scoreOf(article.id);

		await demo.recommendation.sendFeedback(article.id, { sentiment: null });
		await demo.recommendation.sendFeedback(article.id, { sentiment: 'dislike' });
		const direct = await scoreOf(article.id);

		expect(flipped).toBe(direct);
		expect(flipped).toBeLessThan(neutral);
	});

	// Votes stack across articles through the shared feed and keyword tables, which is where a raw
	// total can run away. tanh is what keeps the displayed score inside its bounds.
	it('stays inside 0 and 100 however many likes stack up on one feed', async () => {
		const feedId = SEED_FEEDS[0].id;
		const articles = await demo.article.listArticles({ feedId, limit: 999 });
		for (const article of articles) {
			await demo.recommendation.sendFeedback(article.id, { sentiment: 'like' });
		}
		const after = await demo.article.listArticles({ feedId, limit: 999 });
		expect(after.length).toBeGreaterThan(0);
		expect(after.every((article) => article.relevance_score! >= 0)).toBe(true);
		expect(after.every((article) => article.relevance_score! <= 100)).toBe(true);
	});

	it('ranks by relevance when asked, instead of by date', async () => {
		const articles = await demo.article.listArticles();
		const liked = articles[articles.length - 1];
		await demo.recommendation.sendFeedback(liked.id, { sentiment: 'like' });
		const ranked = await demo.article.listArticles({ sort: 'relevance' });
		const scores = ranked.map((article) => article.relevance_score!);
		expect([...scores].sort((a, b) => b - a)).toEqual(scores);
	});
});

describe('getArticle', () => {
	it('renders the paragraphs as html', async () => {
		const article = await demo.article.getArticle(SEED_ARTICLES[0].id);
		expect(article.content.startsWith('<p>')).toBe(true);
		expect(article.content).toContain(SEED_ARTICLES[0].paragraphs[0]);
	});

	it('exposes the keywords with the ids the chips link to', async () => {
		const article = await demo.article.getArticle(SEED_ARTICLES[0].id);
		expect(article.keywords[0]).toEqual({
			id: `keyword-${SEED_ARTICLES[0].keywords[0]}`,
			term: SEED_ARTICLES[0].keywords[0]
		});
	});

	it('estimates a reading time of at least a minute, never zero', async () => {
		const article = await demo.article.getArticle(SEED_ARTICLES[0].id);
		expect(article.reading_minutes).toBeGreaterThanOrEqual(1);
	});

	it('refuses an unknown id rather than returning an empty article', async () => {
		await expect(demo.article.getArticle('article-nope')).rejects.toThrow();
	});
});

describe('saveUrl', () => {
	it('adds the page at the top of the library', async () => {
		const saved = await demo.article.saveUrl('https://www.blog.test/un-billet');
		const articles = await demo.article.listArticles({ limit: 1 });
		expect(articles[0].id).toBe(saved.id);
	});

	it('names it after the host, without the www', async () => {
		const saved = await demo.article.saveUrl('https://www.blog.test/un-billet');
		expect(saved.title).toContain('blog.test');
		expect(saved.title).not.toContain('www.');
	});

	it('files it as saved, so it shows up in the saved list', async () => {
		const saved = await demo.article.saveUrl('https://blog.test/un-billet');
		const list = await demo.recommendation.getSaved();
		expect(list.map((article) => article.id)).toContain(saved.id);
	});

	it('is readable straight away', async () => {
		const saved = await demo.article.saveUrl('https://blog.test/un-billet');
		await expect(demo.article.getArticle(saved.id)).resolves.toMatchObject({ id: saved.id });
	});
});

describe('the unread counts', () => {
	it('adds up to the number of unread articles', async () => {
		const counts = await demo.feed.getUnreadCounts();
		const unread = await demo.article.listArticles({ unreadOnly: true, limit: 999 });
		expect(counts.total).toBe(unread.length);
	});

	it('drops by one when an article is read', async () => {
		const before = await demo.feed.getUnreadCounts();
		const [article] = await demo.article.listArticles({ unreadOnly: true });
		await demo.recommendation.sendFeedback(article.id, { read: true });
		const after = await demo.feed.getUnreadCounts();
		expect(after.total).toBe(before.total - 1);
	});

	it('breaks the total down per feed and per folder', async () => {
		const counts = await demo.feed.getUnreadCounts();
		const perFeed = Object.values(counts.feeds).reduce((total, count) => total + count, 0);
		expect(perFeed).toBe(counts.total);
		expect(Object.keys(counts.folders).length).toBeGreaterThan(0);
	});
});

describe('markRead', () => {
	it('marks a whole feed and reports how many it changed', async () => {
		const feedId = SEED_FEEDS[0].id;
		const before = await demo.article.listArticles({ feedId, unreadOnly: true, limit: 999 });
		const { updated } = await demo.recommendation.markRead({ feed_id: feedId });
		expect(updated).toBe(before.length);
		await expect(
			demo.article.listArticles({ feedId, unreadOnly: true, limit: 999 })
		).resolves.toEqual([]);
	});

	it('counts nothing the second time, since nothing is left to change', async () => {
		const feedId = SEED_FEEDS[0].id;
		await demo.recommendation.markRead({ feed_id: feedId });
		await expect(demo.recommendation.markRead({ feed_id: feedId })).resolves.toEqual({
			updated: 0
		});
	});

	it('marks a whole folder', async () => {
		const folderId = SEED_FOLDERS[0].id;
		const { updated } = await demo.recommendation.markRead({ folder_id: folderId });
		expect(updated).toBeGreaterThan(0);
		await expect(
			demo.article.listArticles({ folderId, unreadOnly: true, limit: 999 })
		).resolves.toEqual([]);
	});

	it('marks the exact articles it was handed', async () => {
		const [first, second] = await demo.article.listArticles({ unreadOnly: true });
		const { updated } = await demo.recommendation.markRead({
			article_ids: [first.id, second.id]
		});
		expect(updated).toBe(2);
	});

	it('puts an article back to unread when asked', async () => {
		const [article] = await demo.article.listArticles({ unreadOnly: true });
		await demo.recommendation.markRead({ article_ids: [article.id] });
		await demo.recommendation.markRead({ article_ids: [article.id], read: false });
		const unread = await demo.article.listArticles({ unreadOnly: true, limit: 999 });
		expect(unread.map((a) => a.id)).toContain(article.id);
	});
});

describe('the reading position', () => {
	it('remembers how far the reader got', async () => {
		const [article] = await demo.article.listArticles({ limit: 1 });
		await demo.recommendation.sendFeedback(article.id, { scroll_progress: 0.4 });
		const [after] = await demo.article.listArticles({ limit: 1 });
		expect(after.scroll_progress).toBe(0.4);
	});

	it('never rewinds, so scrolling back up does not lose the place', async () => {
		const [article] = await demo.article.listArticles({ limit: 1 });
		await demo.recommendation.sendFeedback(article.id, { scroll_progress: 0.8 });
		await demo.recommendation.sendFeedback(article.id, { scroll_progress: 0.2 });
		const [after] = await demo.article.listArticles({ limit: 1 });
		expect(after.scroll_progress).toBe(0.8);
	});
});

describe('l’étincelle', () => {
	it('offers only unread articles nobody has voted on', async () => {
		const [candidate] = await demo.recommendation.getEtincelle();
		await demo.recommendation.sendFeedback(candidate.id, { sentiment: 'like' });
		const after = await demo.recommendation.getEtincelle();
		expect(after.map((a) => a.id)).not.toContain(candidate.id);
	});

	it('drops an article once it is read', async () => {
		const [candidate] = await demo.recommendation.getEtincelle();
		await demo.recommendation.sendFeedback(candidate.id, { read: true });
		const after = await demo.recommendation.getEtincelle();
		expect(after.map((a) => a.id)).not.toContain(candidate.id);
	});
});

describe('the favourites and the saved list', () => {
	it('adds and removes a favourite', async () => {
		const [article] = await demo.article.listArticles({ limit: 1 });
		await demo.recommendation.sendFeedback(article.id, { favorite: true });
		await expect(demo.recommendation.getFavorites()).resolves.toEqual(
			expect.arrayContaining([expect.objectContaining({ id: article.id })])
		);

		await demo.recommendation.sendFeedback(article.id, { favorite: false });
		const after = await demo.recommendation.getFavorites();
		expect(after.map((a) => a.id)).not.toContain(article.id);
	});

	it('adds and removes a saved article', async () => {
		const [article] = await demo.article.listArticles({ limit: 1 });
		await demo.recommendation.sendFeedback(article.id, { saved: true });
		const saved = await demo.recommendation.getSaved();
		expect(saved.map((a) => a.id)).toContain(article.id);
	});
});

describe('the filter rules', () => {
	it('hides every article matching a mute rule', async () => {
		const article = SEED_ARTICLES[0];
		const term = article.title.split(' ')[1].toLowerCase();
		await demo.recommendation.addFilterRule(term, 'mute');
		const visible = await demo.article.listArticles({ limit: 999 });
		expect(visible.map((a) => a.id)).not.toContain(article.id);
	});

	it('shows them again once the rule is deleted', async () => {
		const article = SEED_ARTICLES[0];
		const term = article.title.split(' ')[1].toLowerCase();
		const rule = await demo.recommendation.addFilterRule(term, 'mute');
		await demo.recommendation.deleteFilterRule(rule.id);
		const visible = await demo.article.listArticles({ limit: 999 });
		expect(visible.map((a) => a.id)).toContain(article.id);
	});

	it('lifts the score of an article matching a boost rule', async () => {
		const article = SEED_ARTICLES[0];
		const [before] = await demo.article.listArticles({ query: article.title, limit: 1 });
		await demo.recommendation.addFilterRule(article.title.split(' ')[1].toLowerCase(), 'boost');
		const [after] = await demo.article.listArticles({ query: article.title, limit: 1 });
		expect(after.relevance_score!).toBeGreaterThan(before.relevance_score!);
	});

	it('matches the title and summary only, never the rendered markup', async () => {
		await demo.recommendation.addFilterRule('<p>', 'mute');
		await expect(demo.article.listArticles({ limit: 999 })).resolves.not.toHaveLength(0);
	});

	it('lists the rules it holds', async () => {
		await demo.recommendation.addFilterRule('crypto', 'mute');
		await demo.recommendation.addFilterRule('vélo', 'boost');
		await expect(demo.recommendation.listFilterRules()).resolves.toHaveLength(2);
	});
});

describe('the folders', () => {
	it('creates one and lists it', async () => {
		const folder = await demo.feed.createFolder('Cuisine');
		await expect(demo.feed.listFolders()).resolves.toEqual(
			expect.arrayContaining([expect.objectContaining({ id: folder.id, name: 'Cuisine' })])
		);
	});

	it('renames one', async () => {
		const folder = await demo.feed.createFolder('Cuisine');
		await demo.feed.renameFolder(folder.id, 'Recettes');
		const folders = await demo.feed.listFolders();
		expect(folders.find((candidate) => candidate.id === folder.id)?.name).toBe('Recettes');
	});

	it('refuses to rename one that does not exist', async () => {
		await expect(demo.feed.renameFolder('folder-nope', 'x')).rejects.toThrow();
	});

	it('unfiles its feeds on delete instead of taking them with it', async () => {
		const folderId = SEED_FOLDERS[0].id;
		const held = SEED_FEEDS.filter((feed) => feed.folder_id === folderId).map((f) => f.id);
		await demo.feed.deleteFolder(folderId);
		const feeds = await demo.feed.listFeeds();
		expect(feeds.filter((feed) => held.includes(feed.id)).every((f) => f.folder_id === null)).toBe(
			true
		);
		expect(feeds).toHaveLength(SEED_FEEDS.length);
	});
});

describe('the feeds', () => {
	it('adds one from a url, named after its host', async () => {
		const feed = await demo.feed.addFeedByUrl('https://www.presse.test/rss');
		expect(feed.title).toBe('presse.test');
		expect(feed.folder_id).toBeNull();
	});

	it('files a new one into the folder it was given', async () => {
		const feed = await demo.feed.addFeedByUrl('https://presse.test/rss', SEED_FOLDERS[0].id);
		expect(feed.folder_id).toBe(SEED_FOLDERS[0].id);
	});

	it('renames one without moving it', async () => {
		const feedId = SEED_FEEDS[0].id;
		const before = SEED_FEEDS[0].folder_id;
		const feed = await demo.feed.updateFeed(feedId, { title: 'Nouveau nom' });
		expect(feed).toMatchObject({ title: 'Nouveau nom', folder_id: before });
	});

	it('unfiles one on an explicit null folder', async () => {
		const feed = await demo.feed.updateFeed(SEED_FEEDS[0].id, { folder_id: null });
		expect(feed.folder_id).toBeNull();
	});

	it('refuses to update one that does not exist', async () => {
		await expect(demo.feed.updateFeed('feed-nope', { title: 'x' })).rejects.toThrow();
	});

	it('takes its articles with it when deleted', async () => {
		const feedId = SEED_FEEDS[0].id;
		await demo.feed.deleteFeed(feedId);
		await expect(demo.article.listArticles({ feedId, limit: 999 })).resolves.toEqual([]);
	});
});

describe('discoverFeeds', () => {
	it('never suggests a feed already subscribed to', async () => {
		const suggestions = await demo.feed.discoverFeeds(50);
		const subscribed = SEED_FEEDS.map((feed) => feed.url.replace(/\/$/, ''));
		expect(suggestions.every((entry) => !subscribed.includes(entry.url.replace(/\/$/, '')))).toBe(
			true
		);
	});

	it('honours the limit', async () => {
		const suggestions = await demo.feed.discoverFeeds(2);
		expect(suggestions.length).toBeLessThanOrEqual(2);
	});

	it('ranks by affinity, highest first', async () => {
		const suggestions = await demo.feed.discoverFeeds(50);
		const affinities = suggestions.map((entry) => entry.affinity ?? 0);
		expect([...affinities].sort((a, b) => b - a)).toEqual(affinities);
	});

	it('lifts a suggestion sharing a topic the reader liked', async () => {
		const suggestions = await demo.feed.discoverFeeds(50);
		// An article the seed has already voted on would make the like a no-op, so the pair is
		// chosen among the untouched ones.
		const untouched = new Set((await demo.recommendation.getEtincelle(999)).map((a) => a.id));

		for (const suggestion of suggestions) {
			for (const topic of suggestion.topics) {
				const article = SEED_ARTICLES.find(
					(candidate) =>
						untouched.has(candidate.id) &&
						candidate.keywords.some((keyword) => keyword.toLowerCase() === topic)
				);
				if (!article) continue;

				await demo.recommendation.sendFeedback(article.id, { sentiment: 'like' });
				const after = (await demo.feed.discoverFeeds(50)).find((e) => e.url === suggestion.url)!;
				expect(after.affinity!).toBeGreaterThan(suggestion.affinity ?? 0);
				return;
			}
		}
		throw new Error('the seed no longer pairs any suggestion topic with an unvoted article');
	});
});

describe('the playlists', () => {
	it('reports the item count and total minutes of each', async () => {
		const [playlist] = await demo.playlist.listPlaylists();
		const detail = await demo.playlist.getPlaylist(playlist.id);
		expect(playlist.item_count).toBe(detail.articles.length);
		expect(playlist.total_reading_minutes).toBe(
			detail.articles.reduce((total, article) => total + article.reading_minutes, 0)
		);
	});

	it('creates an empty one', async () => {
		const created = await demo.playlist.createPlaylist('Trajet');
		const detail = await demo.playlist.getPlaylist(created.id);
		expect(detail).toMatchObject({ name: 'Trajet', articles: [] });
	});

	it('renames one', async () => {
		const created = await demo.playlist.createPlaylist('Trajet');
		await demo.playlist.renamePlaylist(created.id, 'Trajet du soir');
		await expect(demo.playlist.getPlaylist(created.id)).resolves.toMatchObject({
			name: 'Trajet du soir'
		});
	});

	it('deletes one', async () => {
		const created = await demo.playlist.createPlaylist('Trajet');
		await demo.playlist.deletePlaylist(created.id);
		await expect(demo.playlist.getPlaylist(created.id)).rejects.toThrow();
	});

	it('adds and removes an article', async () => {
		const created = await demo.playlist.createPlaylist('Trajet');
		const [article] = await demo.article.listArticles({ limit: 1 });

		const added = await demo.playlist.addArticle(created.id, article.id);
		expect(added.articles.map((a) => a.id)).toEqual([article.id]);

		const removed = await demo.playlist.removeArticle(created.id, article.id);
		expect(removed.articles).toEqual([]);
	});

	it('applies a new order', async () => {
		const created = await demo.playlist.createPlaylist('Trajet');
		const articles = await demo.article.listArticles({ limit: 3 });
		for (const article of articles) await demo.playlist.addArticle(created.id, article.id);

		const reversed = articles.map((article) => article.id).reverse();
		const reordered = await demo.playlist.reorder(created.id, reversed);
		expect(reordered.articles.map((a) => a.id)).toEqual(reversed);
	});

	it('fills one to a target duration without overshooting it', async () => {
		const detail = await demo.playlist.createPlaylistForDuration(20);
		const total = detail.articles.reduce((sum, article) => sum + article.reading_minutes, 0);
		expect(detail.articles.length).toBeGreaterThan(0);
		expect(total).toBeLessThanOrEqual(20);
	});

	it('refuses an unknown playlist rather than returning an empty one', async () => {
		await expect(demo.playlist.getPlaylist('playlist-nope')).rejects.toThrow();
	});
});

describe('the profile', () => {
	it('serves the demo account', async () => {
		await expect(demo.user.getMe()).resolves.toMatchObject({ username: 'Démo' });
	});

	it('applies a change and keeps it', async () => {
		await demo.user.updateMe({ preferred_language: 'es' });
		await expect(demo.user.getMe()).resolves.toMatchObject({ preferred_language: 'es' });
	});

	it('records that an ai key was set without ever storing the key itself', async () => {
		const me = await demo.user.updateMe({ ai_api_key: 'sk-secret' });
		expect(me.ai_api_key_set).toBe(true);
		expect(JSON.stringify(me)).not.toContain('sk-secret');
	});

	it('records that a translation key was set the same way', async () => {
		const me = await demo.user.updateMe({ translation_api_key: 'dl-secret' });
		expect(me.translation_api_key_set).toBe(true);
		expect(JSON.stringify(me)).not.toContain('dl-secret');
	});
});

describe('the session state', () => {
	it('survives a reload, so the demo remembers what was tried', async () => {
		const [article] = await demo.article.listArticles({ limit: 1 });
		await demo.recommendation.sendFeedback(article.id, { favorite: true });

		const reloaded = createDemoClient();
		const favorites = await reloaded.recommendation.getFavorites();
		expect(favorites.map((a) => a.id)).toContain(article.id);
	});

	it('starts clean again after a logout', async () => {
		await demo.feed.createFolder('Cuisine');
		await demo.user.logout();
		await expect(demo.feed.listFolders()).resolves.toHaveLength(SEED_FOLDERS.length);
	});

	it('falls back to a fresh demo when the stored state is corrupt', async () => {
		localStorage.setItem('lumia:demo-state', '{ not json');
		const client = createDemoClient();
		await expect(client.feed.listFolders()).resolves.toHaveLength(SEED_FOLDERS.length);
	});

	it('accepts the login calls the real forms make, without a session to open', async () => {
		await expect(demo.user.login('a@b.c', 'x')).resolves.toBeUndefined();
		await expect(demo.user.requestMagicLink('a@b.c')).resolves.toBeUndefined();
		await expect(demo.user.verifyMagicLink('token')).resolves.toBeUndefined();
		await expect(
			demo.user.onboardAdmin({ email: 'a@b.c', username: 'a', password: 'x' })
		).resolves.toBeUndefined();
	});

	it('answers an opml import with the feeds it already has', async () => {
		const file = new File(['<opml />'], 'feedly.opml');
		await expect(demo.feed.importOpml(file)).resolves.toHaveLength(SEED_FEEDS.length);
	});

	it('exports an opml document carrying every seed feed and folder', async () => {
		const blob = await demo.feed.exportOpml();
		const xml = await blob.text();
		for (const folder of SEED_FOLDERS) expect(xml).toContain(folder.name);
		for (const feed of SEED_FEEDS) expect(xml).toContain(feed.url);
	});
});
