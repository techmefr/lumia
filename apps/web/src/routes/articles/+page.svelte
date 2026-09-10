<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import type { ArticleSummary, Feed, Folder, UnreadCounts } from '@lumia/core';
	import { Button, Input, toast } from '@lumia/ui';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Inbox from '@lucide/svelte/icons/inbox';
	import X from '@lucide/svelte/icons/x';
	import Search from '@lucide/svelte/icons/search';
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import Plus from '@lucide/svelte/icons/plus';
	import BookOpen from '@lucide/svelte/icons/book-open';
	import LayoutTemplate from '@lucide/svelte/icons/layout-template';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import { bindShortcuts } from '$technical/keyboard/shortcuts';
	import { watchCompactViewport } from '$technical/layout/breakpoints';
	import ArticleGrid from '$domain/article/article-grid.svelte';
	import SectionChips from '$domain/article/section-chips.svelte';
	import FlipReader from '$domain/article/flip-reader.svelte';
	import FeedSidebar from '$domain/feed/feed-sidebar.svelte';

	const PAGE_SIZE = 24;

	let articles = $state<ArticleSummary[]>([]);
	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let unread = $state<UnreadCounts>({ total: 0, feeds: {}, folders: {} });
	let selectedFolderId = $state('');
	let selectedFeedId = $state('');
	let authorId = $state<string | undefined>(undefined);
	let categoryId = $state<string | undefined>(undefined);
	let keywordId = $state<string | undefined>(undefined);
	// Kept as kind + name rather than a formatted string, so the chip follows a language change.
	let filterKind = $state<'author' | 'category' | 'keyword' | null>(null);
	let filterName = $state('');
	let searchInput = $state('');
	let appliedQuery = $state('');
	let unreadOnly = $state(false);
	let loading = $state(true);
	let loadingMore = $state(false);
	let hasMore = $state(false);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
	let cursor = $state(-1);
	let searchEl = $state<HTMLInputElement | null>(null);
	let sort = $state<'recent' | 'relevance'>('recent');
	let flipping = $state(false);
	let compact = $state(false);

	const filterLabel = $derived(
		filterKind === 'author'
			? t('articles.filterAuthor', { name: filterName })
			: filterKind === 'category'
				? t('articles.filterCategory', { name: filterName })
				: filterKind === 'keyword'
					? t('articles.filterKeyword', { name: filterName })
					: null
	);

	const currentScope = $derived(
		selectedFeedId
			? { feed_id: selectedFeedId }
			: selectedFolderId
				? { folder_id: selectedFolderId }
				: null
	);

	function params(offset: number) {
		return {
			folderId: selectedFolderId || undefined,
			feedId: selectedFeedId || undefined,
			authorId,
			categoryId,
			keywordId,
			query: appliedQuery.length >= 2 ? appliedQuery : undefined,
			unreadOnly: unreadOnly || undefined,
			sort,
			limit: PAGE_SIZE,
			offset
		};
	}

	function setSort(next: 'recent' | 'relevance') {
		if (sort === next) return;
		sort = next;
		void loadArticles();
	}

	async function loadArticles() {
		loading = true;
		error = null;
		cursor = -1;
		try {
			const loaded = await lumia.article.listArticles(params(0));
			articles = loaded;
			// A full page back means there may be more; a short page means we've reached the end.
			hasMore = loaded.length === PAGE_SIZE;
		} catch {
			error = 'articles.loadFailed';
		} finally {
			loading = false;
		}
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;
		try {
			const next = await lumia.article.listArticles(params(articles.length));
			articles = [...articles, ...next];
			hasMore = next.length === PAGE_SIZE;
		} catch {
			error = 'common.loadMoreFailed';
		} finally {
			loadingMore = false;
		}
	}

	async function refreshUnread() {
		try {
			unread = await lumia.feed.getUnreadCounts();
		} catch {
			// Counts are decoration: a failure here must not break the list.
		}
	}

	function clearTagFilter() {
		authorId = undefined;
		categoryId = undefined;
		keywordId = undefined;
		filterKind = null;
		void loadArticles();
	}

	function selectAll() {
		selectedFolderId = '';
		selectedFeedId = '';
		clearTagFilter();
	}

	function selectFolder(folderId: string) {
		selectedFolderId = selectedFolderId === folderId ? '' : folderId;
		selectedFeedId = '';
		authorId = categoryId = keywordId = undefined;
		filterKind = null;
		void loadArticles();
	}

	function selectFeed(feedId: string) {
		selectedFeedId = selectedFeedId === feedId ? '' : feedId;
		selectedFolderId = '';
		authorId = categoryId = keywordId = undefined;
		filterKind = null;
		void loadArticles();
	}

	function submitSearch(event: SubmitEvent) {
		event.preventDefault();
		appliedQuery = searchInput.trim();
		void loadArticles();
	}

	function clearSearch() {
		searchInput = '';
		appliedQuery = '';
		void loadArticles();
	}

	function toggleUnreadOnly() {
		unreadOnly = !unreadOnly;
		void loadArticles();
	}

	async function markScopeRead(scope: { feed_id?: string; folder_id?: string } | null) {
		// No feed or folder selected means "Tout": every unread article across every feed, not just
		// the page currently on screen, otherwise a reader with several hundred unread articles would
		// see the button clear the visible batch and leave the rest looking untouched. It is also the
		// one scope with no natural ceiling, so it is the one that asks first; a single feed or
		// folder stays a quick, undoable action.
		const target = scope ?? { all: true };
		if (scope === null && unread.total > 10) {
			const confirmed = confirm(t('articles.confirmMarkAllRead', { count: unread.total }));
			if (!confirmed) return;
		}
		const previous = articles.map((article) => ({ id: article.id, read: article.read }));
		try {
			await lumia.recommendation.markRead(target);
			articles = articles.map((article) => ({ ...article, read: true }));
			await refreshUnread();
			toast(t('articles.markedRead'), {
				action: {
					label: t('common.undo'),
					run: async () => {
						await lumia.recommendation.markRead({ ...target, read: false });
						const wasRead = new Map(previous.map((entry) => [entry.id, entry.read]));
						articles = articles.map((article) => ({
							...article,
							read: wasRead.get(article.id) ?? false
						}));
						await refreshUnread();
					}
				}
			});
			if (unreadOnly) void loadArticles();
		} catch {
			toast(t('articles.markReadFailed'), { tone: 'destructive' });
		}
	}

	async function markFeedRead(feedId: string) {
		await markScopeRead({ feed_id: feedId });
	}

	async function markFolderRead(folderId: string) {
		await markScopeRead({ folder_id: folderId });
	}

	function moveCursor(delta: number) {
		if (articles.length === 0) return;
		const next = cursor + delta;
		cursor = Math.min(Math.max(next, 0), articles.length - 1);
	}

	async function openCursor() {
		const article = articles[cursor];
		if (article) await goto(`${base}/articles/${article.id}`);
	}

	async function markCursorRead() {
		const article = articles[cursor];
		if (!article) return;
		const read = !article.read;
		await lumia.recommendation.sendFeedback(article.id, { read });
		articles = articles.map((item) => (item.id === article.id ? { ...item, read } : item));
		await refreshUnread();
	}

	async function saveCursor() {
		const article = articles[cursor];
		if (!article) return;
		await lumia.recommendation.sendFeedback(article.id, { saved: true });
		toast(t('etincelle.savedToast'));
	}

	onMount(() => {
		if (!requireAuth()) return;
		const search = page.url.searchParams;
		selectedFolderId = search.get('folder_id') ?? '';
		selectedFeedId = search.get('feed_id') ?? '';
		authorId = search.get('author_id') ?? undefined;
		categoryId = search.get('category_id') ?? undefined;
		keywordId = search.get('keyword_id') ?? undefined;
		if (authorId) {
			filterKind = 'author';
			filterName = search.get('author_name') ?? '';
		} else if (categoryId) {
			filterKind = 'category';
			filterName = search.get('category_name') ?? '';
		} else if (keywordId) {
			filterKind = 'keyword';
			filterName = search.get('keyword_term') ?? '';
		}

		void Promise.all([lumia.feed.listFolders(), lumia.feed.listFeeds()]).then(([f, fe]) => {
			folders = f;
			feeds = fe;
		});
		void loadArticles();
		void refreshUnread();

		// One column renders "Récents" and "Kiosque" identically, so a narrow screen offers a single
		// mode. Handled here rather than by hiding the control in CSS: a mode chosen on a wide window
		// would otherwise stay in effect, sorting a mobile list by relevance with nothing on screen
		// saying so and no way left to change it.
		const stopWatchingViewport = watchCompactViewport((isCompact) => {
			compact = isCompact;
			if (isCompact) setSort('recent');
		});

		const unbindShortcuts = bindShortcuts({
			f: () => (flipping = articles.length > 0),
			j: () => moveCursor(1),
			k: () => moveCursor(-1),
			o: () => void openCursor(),
			enter: () => void openCursor(),
			m: () => void markCursorRead(),
			s: () => void saveCursor(),
			u: toggleUnreadOnly,
			'/': () => searchEl?.focus()
		});

		return () => {
			stopWatchingViewport();
			unbindShortcuts();
		};
	});
</script>

<div class="flex flex-col gap-4 sm:flex-row sm:gap-6">
	<FeedSidebar
		{folders}
		{feeds}
		{unread}
		{selectedFolderId}
		{selectedFeedId}
		onSelectAll={selectAll}
		onSelectFolder={selectFolder}
		onSelectFeed={selectFeed}
		onMarkFeedRead={markFeedRead}
		onMarkFolderRead={markFolderRead}
	/>

	<div class="flex min-w-0 flex-1 flex-col gap-6">
		<div class="flex flex-wrap items-center justify-between gap-3">
			<h1 class="flex items-center gap-2 text-2xl font-semibold">
				<Newspaper class="size-6 text-primary" />
				{t('articles.title')}
				{#if unread.total > 0}
					<span class="rounded-full bg-primary/10 px-2 py-0.5 text-sm font-medium text-primary">
						{t('articles.unreadBadge', { count: unread.total })}
					</span>
				{/if}
			</h1>
			<div class="flex flex-wrap items-center gap-2">
				{#if !compact}
					<div
						data-test-display-mode
						class="flex overflow-hidden rounded-md border"
						role="group"
						aria-label={t('articles.sortGroup')}
					>
						<button
							type="button"
							onclick={() => setSort('recent')}
							aria-pressed={sort === 'recent'}
							class="min-h-9 px-3 text-sm font-medium transition-colors {sort === 'recent'
								? 'bg-primary text-primary-foreground'
								: 'hover:bg-secondary'}"
						>
							{t('articles.sortRecent')}
						</button>
						<button
							type="button"
							onclick={() => setSort('relevance')}
							aria-pressed={sort === 'relevance'}
							class="flex min-h-9 items-center gap-1.5 border-l px-3 text-sm font-medium transition-colors {sort ===
							'relevance'
								? 'bg-primary text-primary-foreground'
								: 'hover:bg-secondary'}"
						>
							<LayoutTemplate class="size-4" />
							{t('articles.sortKiosk')}
						</button>
					</div>
				{/if}
				<Button
					data-test-flip
					variant="outline"
					size="sm"
					onclick={() => (flipping = true)}
					disabled={articles.length === 0}
				>
					<BookOpen class="size-4" />
					{t('articles.flip')}
				</Button>
				<Button variant={unreadOnly ? 'default' : 'outline'} size="sm" onclick={toggleUnreadOnly}>
					{t('articles.unreadOnly')}
				</Button>
				<Button variant="outline" size="sm" onclick={() => markScopeRead(currentScope)}>
					<CheckCheck class="size-4" />
					{t('feeds.markAllRead')}
				</Button>
			</div>
		</div>

		<SectionChips
			{folders}
			{unread}
			{selectedFolderId}
			onSelectAll={selectAll}
			onSelectFolder={selectFolder}
		/>

		<form class="flex items-center gap-2" onsubmit={submitSearch} role="search">
			<label for="article-search" class="sr-only">{t('articles.searchLabel')}</label>
			<Input
				id="article-search"
				bind:ref={searchEl}
				bind:value={searchInput}
				type="search"
				placeholder={t('articles.searchPlaceholder')}
				class="max-w-sm"
			/>
			<Button type="submit" variant="secondary" size="sm">
				<Search class="size-4" />
				{t('articles.search')}
			</Button>
			{#if appliedQuery}
				<Button type="button" variant="ghost" size="sm" onclick={clearSearch}>
					<X class="size-4" />
					{t('articles.clear')}
				</Button>
			{/if}
		</form>

		{#if appliedQuery}
			<p class="text-sm text-muted-foreground">
				{t('articles.results', {
					query: appliedQuery,
					count: `${articles.length}${hasMore ? '+' : ''}`
				})}
			</p>
		{/if}

		{#if filterLabel}
			<button
				onclick={clearTagFilter}
				class="flex w-fit items-center gap-1.5 rounded-full bg-secondary px-3 py-1 text-sm text-secondary-foreground transition-colors hover:bg-secondary/70"
			>
				{filterLabel}
				<X class="size-3.5" />
			</button>
		{/if}

		{#if error}
			<p role="alert" class="text-sm text-destructive">{t(error)}</p>
		{/if}

		<ArticleGrid {articles} {loading} {cursor} hero={sort === 'relevance'}>
			{#snippet empty()}
				<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
					<p class="flex items-center gap-2 text-sm text-muted-foreground">
						<Inbox class="size-4" />
						{#if appliedQuery}
							{t('articles.emptySearch', { query: appliedQuery })}
						{:else if unreadOnly}
							{t('articles.emptyUnread')}
						{:else}
							{t('articles.emptyNoFeeds')}
						{/if}
					</p>
					<div class="flex flex-wrap gap-2">
						{#if appliedQuery}
							<Button size="sm" variant="secondary" onclick={clearSearch}>
								{t('articles.clearSearch')}
							</Button>
						{/if}
						{#if unreadOnly}
							<Button size="sm" variant="secondary" onclick={toggleUnreadOnly}>
								{t('articles.showAll')}
							</Button>
						{/if}
						<Button size="sm" href="{base}/feeds">
							<Plus class="size-4" />
							{t('articles.addFeeds')}
						</Button>
					</div>
				</div>
			{/snippet}

			{#snippet footer()}
				{#if hasMore}
					<div class="mt-6 flex justify-center">
						<Button variant="outline" onclick={loadMore} disabled={loadingMore}>
							{loadingMore ? t('common.loading') : t('common.loadMore')}
						</Button>
					</div>
				{/if}
			{/snippet}
		</ArticleGrid>

		<p class="text-xs text-muted-foreground">
			{t('articles.shortcuts')} <kbd>j</kbd>/<kbd>k</kbd> {t('articles.shortcutNavigate')} ·
			<kbd>o</kbd>
			{t('articles.shortcutOpen')} · <kbd>m</kbd> {t('articles.shortcutRead')} · <kbd>s</kbd>
			{t('articles.shortcutSave')} · <kbd>u</kbd> {t('articles.shortcutUnread')} · <kbd>f</kbd>
			{t('articles.shortcutFlip')} · <kbd>/</kbd> {t('articles.shortcutSearch')}
		</p>
	</div>
</div>

{#if flipping}
	<FlipReader
		{articles}
		startIndex={Math.max(cursor, 0)}
		onClose={() => (flipping = false)}
		onPage={(index) => (cursor = index)}
	/>
{/if}
