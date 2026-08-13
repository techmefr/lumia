<script lang="ts">
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
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { bindShortcuts } from '$technical/keyboard/shortcuts';
	import ArticleGrid from '$domain/article/article-grid.svelte';
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
	let filterLabel = $state<string | null>(null);
	let searchInput = $state('');
	let appliedQuery = $state('');
	let unreadOnly = $state(false);
	let loading = $state(true);
	let loadingMore = $state(false);
	let hasMore = $state(false);
	let error = $state<string | null>(null);
	let cursor = $state(-1);
	let searchEl = $state<HTMLInputElement | null>(null);

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
			limit: PAGE_SIZE,
			offset
		};
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
			error = 'Impossible de charger les articles.';
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
			error = 'Impossible de charger la suite.';
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
		filterLabel = null;
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
		filterLabel = null;
		void loadArticles();
	}

	function selectFeed(feedId: string) {
		selectedFeedId = selectedFeedId === feedId ? '' : feedId;
		selectedFolderId = '';
		authorId = categoryId = keywordId = undefined;
		filterLabel = null;
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
		const target = scope ?? { article_ids: articles.map((article) => article.id) };
		const previous = articles.map((article) => ({ id: article.id, read: article.read }));
		try {
			await lumia.recommendation.markRead(target);
			articles = articles.map((article) => ({ ...article, read: true }));
			await refreshUnread();
			toast('Marqué comme lu.', {
				action: {
					label: 'Annuler',
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
			toast('Impossible de marquer comme lu.', { tone: 'destructive' });
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
		if (article) await goto(`/articles/${article.id}`);
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
		toast('Ajouté à « À lire ».');
	}

	onMount(() => {
		if (!requireAuth()) return;
		const search = page.url.searchParams;
		selectedFolderId = search.get('folder_id') ?? '';
		selectedFeedId = search.get('feed_id') ?? '';
		authorId = search.get('author_id') ?? undefined;
		categoryId = search.get('category_id') ?? undefined;
		keywordId = search.get('keyword_id') ?? undefined;
		if (authorId) filterLabel = `Auteur : ${search.get('author_name') ?? ''}`.trim();
		else if (categoryId) filterLabel = `Catégorie : ${search.get('category_name') ?? ''}`.trim();
		else if (keywordId) filterLabel = `Mot-clé : ${search.get('keyword_term') ?? ''}`.trim();

		void Promise.all([lumia.feed.listFolders(), lumia.feed.listFeeds()]).then(([f, fe]) => {
			folders = f;
			feeds = fe;
		});
		void loadArticles();
		void refreshUnread();

		return bindShortcuts({
			j: () => moveCursor(1),
			k: () => moveCursor(-1),
			o: () => void openCursor(),
			enter: () => void openCursor(),
			m: () => void markCursorRead(),
			s: () => void saveCursor(),
			u: toggleUnreadOnly,
			'/': () => searchEl?.focus()
		});
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
				Articles
				{#if unread.total > 0}
					<span class="rounded-full bg-primary/10 px-2 py-0.5 text-sm font-medium text-primary">
						{unread.total} non lus
					</span>
				{/if}
			</h1>
			<div class="flex flex-wrap items-center gap-2">
				<Button variant={unreadOnly ? 'default' : 'outline'} size="sm" onclick={toggleUnreadOnly}>
					Non lus seulement
				</Button>
				<Button variant="outline" size="sm" onclick={() => markScopeRead(currentScope)}>
					<CheckCheck class="size-4" />
					Tout marquer comme lu
				</Button>
			</div>
		</div>

		<form class="flex items-center gap-2" onsubmit={submitSearch} role="search">
			<label for="article-search" class="sr-only">Rechercher un article</label>
			<Input
				id="article-search"
				bind:ref={searchEl}
				bind:value={searchInput}
				type="search"
				placeholder="Rechercher (touche /)"
				class="max-w-sm"
			/>
			<Button type="submit" variant="secondary" size="sm">
				<Search class="size-4" />
				Rechercher
			</Button>
			{#if appliedQuery}
				<Button type="button" variant="ghost" size="sm" onclick={clearSearch}>
					<X class="size-4" />
					Effacer
				</Button>
			{/if}
		</form>

		{#if appliedQuery}
			<p class="text-sm text-muted-foreground">
				Résultats pour « {appliedQuery} » — {articles.length}{hasMore ? '+' : ''} article{articles.length >
				1
					? 's'
					: ''}.
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
			<p role="alert" class="text-sm text-destructive">{error}</p>
		{/if}

		<ArticleGrid {articles} {loading} {cursor}>
			{#snippet empty()}
				<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
					<p class="flex items-center gap-2 text-sm text-muted-foreground">
						<Inbox class="size-4" />
						{#if appliedQuery}
							Aucun article ne correspond à « {appliedQuery} ».
						{:else if unreadOnly}
							Tout est lu. Rien de neuf pour le moment.
						{:else}
							Aucun article : il faut d'abord des flux.
						{/if}
					</p>
					<div class="flex flex-wrap gap-2">
						{#if appliedQuery}
							<Button size="sm" variant="secondary" onclick={clearSearch}>Effacer la recherche</Button>
						{/if}
						{#if unreadOnly}
							<Button size="sm" variant="secondary" onclick={toggleUnreadOnly}>
								Afficher tous les articles
							</Button>
						{/if}
						<Button size="sm" href="/feeds">
							<Plus class="size-4" />
							Ajouter des flux
						</Button>
					</div>
				</div>
			{/snippet}

			{#snippet footer()}
				{#if hasMore}
					<div class="mt-6 flex justify-center">
						<Button variant="outline" onclick={loadMore} disabled={loadingMore}>
							{loadingMore ? 'Chargement…' : 'Charger plus'}
						</Button>
					</div>
				{/if}
			{/snippet}
		</ArticleGrid>

		<p class="text-xs text-muted-foreground">
			Raccourcis : <kbd>j</kbd>/<kbd>k</kbd> naviguer · <kbd>o</kbd> ouvrir · <kbd>m</kbd> lu/non lu ·
			<kbd>s</kbd> à lire · <kbd>u</kbd> non lus · <kbd>/</kbd> rechercher
		</p>
	</div>
</div>
