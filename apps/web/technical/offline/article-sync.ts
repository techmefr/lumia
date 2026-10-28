import type { ArticleDetail, ArticleSummary, ListArticlesParams } from '@lumia/core';
import {
	listStoredArticles,
	putStoredArticles,
	removeStoredArticles,
	type StoredArticle
} from './article-store';
import { listPendingFeedback } from './feedback-queue';
import { articleImageUrls } from './image-urls';

const PAGE_SIZE = 50;

export interface ArticleSyncApi {
	getSaved(limit: number, offset: number): Promise<ArticleSummary[]>;
	listArticles(params: ListArticlesParams): Promise<ArticleSummary[]>;
	getArticle(articleId: string): Promise<ArticleDetail>;
}

export interface ArticleSyncResult {
	stored: number;
	removed: number;
}

async function collectSaved(api: ArticleSyncApi, limit: number): Promise<ArticleSummary[]> {
	const collected: ArticleSummary[] = [];
	while (collected.length < limit) {
		const size = Math.min(PAGE_SIZE, limit - collected.length);
		const page = await api.getSaved(size, collected.length);
		collected.push(...page);
		if (page.length < size) break;
	}
	return collected;
}

async function collectUnread(
	api: ArticleSyncApi,
	limit: number,
	excluded: Set<string>
): Promise<ArticleSummary[]> {
	if (limit <= 0) return [];
	const unread = await api.listArticles({ unreadOnly: true, limit: limit + excluded.size });
	return unread.filter((summary) => !excluded.has(summary.id)).slice(0, limit);
}

export async function syncOfflineArticles(
	api: ArticleSyncApi,
	limit: number,
	syncImages: (urls: string[]) => Promise<void>
): Promise<ArticleSyncResult> {
	const existing = new Map((await listStoredArticles()).map((entry) => [entry.id, entry]));

	if (limit <= 0) {
		await removeStoredArticles([...existing.keys()]);
		await syncImages([]);
		return { stored: 0, removed: existing.size };
	}

	const saved = await collectSaved(api, limit);
	const unread = await collectUnread(api, limit - saved.length, new Set(saved.map((a) => a.id)));
	const wanted = [
		...saved.map((summary) => ({ summary, listedAs: 'saved' as const })),
		...unread.map((summary) => ({ summary, listedAs: 'unread' as const }))
	];

	const pending = new Set((await listPendingFeedback()).map((entry) => entry.articleId));
	const entries: StoredArticle[] = [];
	for (const { summary, listedAs } of wanted) {
		const kept = existing.get(summary.id);
		if (!kept) {
			entries.push({ id: summary.id, article: await api.getArticle(summary.id), listedAs });
			continue;
		}
		const article = pending.has(summary.id)
			? kept.article
			: { ...kept.article, read: summary.read, scroll_progress: summary.scroll_progress };
		entries.push({ id: summary.id, article, listedAs });
	}

	const wantedIds = new Set(wanted.map(({ summary }) => summary.id));
	const obsolete = [...existing.keys()].filter((id) => !wantedIds.has(id));

	await putStoredArticles(entries);
	await removeStoredArticles(obsolete);
	await syncImages([...new Set(entries.flatMap((entry) => articleImageUrls(entry.article)))]);

	return { stored: entries.length, removed: obsolete.length };
}
