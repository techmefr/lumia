import { apiBaseUrl, isDemo, lumia } from './client';

/**
 * Feed icons are proxied by the API behind bearer auth, and an `<img src>` cannot carry an
 * Authorization header. So each icon is fetched once with the token, turned into an object URL,
 * and cached for the life of the page.
 */
class FeedIconStore {
	private urls = $state<Record<string, string>>({});
	private pending = new Set<string>();
	private missing = new Set<string>();

	/** Returns the cached object URL, kicking off the fetch the first time it's asked for. */
	get(feedId: string): string | null {
		if (this.urls[feedId]) return this.urls[feedId];
		if (!this.pending.has(feedId) && !this.missing.has(feedId)) void this.load(feedId);
		return null;
	}

	reset(): void {
		for (const url of Object.values(this.urls)) URL.revokeObjectURL(url);
		this.urls = {};
		this.pending.clear();
		this.missing.clear();
	}

	private async load(feedId: string): Promise<void> {
		// No API in the demo build: the cards fall back to the source initial.
		if (isDemo) {
			this.missing.add(feedId);
			return;
		}
		this.pending.add(feedId);
		try {
			const base = apiBaseUrl;
			const token = lumia.tokenStore.getAccessToken();
			const response = await fetch(`${base}/feeds/${feedId}/icon`, {
				headers: token ? { authorization: `Bearer ${token}` } : {}
			});
			if (!response.ok) {
				// A feed with no icon is the common case, not an error worth retrying.
				this.missing.add(feedId);
				return;
			}
			const blob = await response.blob();
			const previous = this.urls[feedId];
			if (previous) URL.revokeObjectURL(previous);
			this.urls = { ...this.urls, [feedId]: URL.createObjectURL(blob) };
		} catch {
			this.missing.add(feedId);
		} finally {
			this.pending.delete(feedId);
		}
	}
}

export const feedIcons = new FeedIconStore();
