import type { ArticleDetail, ArticleSummary } from '@lumia/core';
import { sanitizeArticleHtmlForOffline } from '@lumia/core';
import type { CachedArticleRecord, OfflineDatabase } from '$technical/offline/offline-database';

/**
 * Default cap on how much offline article text one reader can keep at once. Text only — no
 * images — so this is generous: at a few kilobytes per article, it comfortably covers a saved
 * list's worth of reading without the account's whole offline footprint being open-ended.
 */
export const DEFAULT_OFFLINE_CAP_BYTES = 20 * 1024 * 1024;

/**
 * Thrown by `makeAvailable` when caching an article would cross `capBytes`. The cap is a promise
 * the storage indicator makes to the reader, not a soft target: it is enforced rather than merely
 * displayed, and going over it is never silent.
 */
export class OfflineQuotaExceededError extends Error {
	constructor(
		public readonly bytesNeeded: number,
		public readonly bytesAvailable: number
	) {
		super('offline storage cap reached');
		this.name = 'OfflineQuotaExceededError';
	}
}

function byteLength(text: string): number {
	return new TextEncoder().encode(text).length;
}

/**
 * The reader-facing half of offline reading: which articles are kept for offline reading, how
 * much room they take, and the two ways of putting one there. A plain class over `OfflineDatabase`
 * so it is unit-testable against the in-memory double and so the service worker never has to carry
 * this decision logic — it only ever reads back what this already decided to store.
 */
export class OfflineLibrary {
	private db: OfflineDatabase;
	capBytes = $state(DEFAULT_OFFLINE_CAP_BYTES);
	records = $state<CachedArticleRecord[]>([]);
	loading = $state(false);

	constructor(db: OfflineDatabase, capBytes: number = DEFAULT_OFFLINE_CAP_BYTES) {
		this.db = db;
		this.capBytes = capBytes;
	}

	get bytesUsed(): number {
		return this.records.reduce((total, record) => total + record.bytes, 0);
	}

	get offlineIds(): string[] {
		return this.records.map((record) => record.id);
	}

	isOffline(articleId: string): boolean {
		return this.records.some((record) => record.id === articleId);
	}

	async init(): Promise<void> {
		this.loading = true;
		try {
			this.records = await this.db.listArticles();
		} finally {
			this.loading = false;
		}
	}

	/** The stored copy, for the article page to fall back to when the network has nothing to give. */
	async getContent(articleId: string): Promise<CachedArticleRecord | null> {
		return this.db.getArticle(articleId);
	}

	/**
	 * Stores one article for offline reading — explicit, one article at a time. Images are stripped
	 * before the byte count is even taken: they are the bulk of an article's weight and the one
	 * thing unreachable with no signal, so a reader who opts in gets the words, not broken
	 * placeholders eating the budget meant for more articles.
	 */
	async makeAvailable(article: ArticleDetail): Promise<void> {
		if (this.isOffline(article.id)) return;
		const content = sanitizeArticleHtmlForOffline(article.content);
		const bytes = byteLength(content);
		if (this.bytesUsed + bytes > this.capBytes) {
			throw new OfflineQuotaExceededError(bytes, this.capBytes - this.bytesUsed);
		}
		const record: CachedArticleRecord = {
			id: article.id,
			title: article.title,
			sourceLabel: article.source_label,
			content,
			imageUrl: article.image_url,
			readingMinutes: article.reading_minutes,
			savedAt: Date.now(),
			bytes
		};
		await this.db.putArticle(record);
		this.records = [...this.records, record];
	}

	async makeUnavailable(articleId: string): Promise<void> {
		if (!this.isOffline(articleId)) return;
		await this.db.deleteArticle(articleId);
		this.records = this.records.filter((record) => record.id !== articleId);
	}

	/**
	 * "Make all available offline" for the saved list. Caches as many `summaries` as fit under the
	 * cap, in the order given, and reports exactly which ones it could not — once the cap is hit,
	 * every article after it is reported skipped too, rather than the call quietly stopping partway
	 * with no way for the UI to say why the list is incomplete.
	 */
	async makeAllAvailable(
		summaries: ArticleSummary[],
		fetchDetail: (articleId: string) => Promise<ArticleDetail>
	): Promise<{ cached: string[]; skipped: string[] }> {
		const cached: string[] = [];
		const skipped: string[] = [];

		for (let index = 0; index < summaries.length; index += 1) {
			const summary = summaries[index];
			if (this.isOffline(summary.id)) {
				cached.push(summary.id);
				continue;
			}
			try {
				const detail = await fetchDetail(summary.id);
				await this.makeAvailable(detail);
				cached.push(summary.id);
			} catch (error) {
				skipped.push(summary.id);
				if (error instanceof OfflineQuotaExceededError) {
					skipped.push(...summaries.slice(index + 1).map((remaining) => remaining.id));
					break;
				}
			}
		}

		return { cached, skipped };
	}
}
