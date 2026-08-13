<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import type { ArticleSummary, Feed, Folder } from '@lumia/core';
	import { ArticleCard } from '@lumia/ui';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Inbox from '@lucide/svelte/icons/inbox';
	import X from '@lucide/svelte/icons/x';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { accentHueForFeed } from '$domain/article/accent-hue';

	let articles = $state<ArticleSummary[]>([]);
	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let selectedFolderId = $state('');
	let selectedFeedId = $state('');
	let authorId = $state<string | undefined>(undefined);
	let categoryId = $state<string | undefined>(undefined);
	let keywordId = $state<string | undefined>(undefined);
	let filterLabel = $state<string | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadArticles() {
		loading = true;
		error = null;
		try {
			articles = await lumia.article.listArticles({
				folderId: selectedFolderId || undefined,
				feedId: selectedFeedId || undefined,
				authorId,
				categoryId,
				keywordId
			});
		} catch {
			error = 'Impossible de charger les articles.';
		} finally {
			loading = false;
		}
	}

	function clearTagFilter() {
		authorId = undefined;
		categoryId = undefined;
		keywordId = undefined;
		filterLabel = null;
		void loadArticles();
	}

	onMount(() => {
		if (!requireAuth()) return;
		const params = page.url.searchParams;
		selectedFolderId = params.get('folder_id') ?? '';
		selectedFeedId = params.get('feed_id') ?? '';
		authorId = params.get('author_id') ?? undefined;
		categoryId = params.get('category_id') ?? undefined;
		keywordId = params.get('keyword_id') ?? undefined;
		if (authorId) filterLabel = `Auteur : ${params.get('author_name') ?? ''}`.trim();
		else if (categoryId) filterLabel = `Catégorie : ${params.get('category_name') ?? ''}`.trim();
		else if (keywordId) filterLabel = `Mot-clé : ${params.get('keyword_term') ?? ''}`.trim();

		void Promise.all([lumia.feed.listFolders(), lumia.feed.listFeeds()]).then(([f, fe]) => {
			folders = f;
			feeds = fe;
		});
		void loadArticles();
	});
</script>

<div class="flex flex-col gap-6">
	<div class="flex flex-wrap items-end justify-between gap-4">
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Newspaper class="size-6 text-primary" />
			Articles
		</h1>
		<div class="flex gap-3">
			<select
				bind:value={selectedFolderId}
				onchange={loadArticles}
				class="h-9 rounded-md border border-input bg-background px-3 text-sm"
			>
				<option value="">Tous les dossiers</option>
				{#each folders as folder (folder.id)}
					<option value={folder.id}>{folder.name}</option>
				{/each}
			</select>
			<select
				bind:value={selectedFeedId}
				onchange={loadArticles}
				class="h-9 rounded-md border border-input bg-background px-3 text-sm"
			>
				<option value="">Tous les flux</option>
				{#each feeds as feed (feed.id)}
					<option value={feed.id}>{feed.title}</option>
				{/each}
			</select>
		</div>
	</div>

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
		<p class="text-sm text-destructive">{error}</p>
	{/if}

	{#if loading}
		<p class="text-sm text-muted-foreground">Chargement…</p>
	{:else if articles.length === 0}
		<p class="flex items-center gap-2 text-sm text-muted-foreground">
			<Inbox class="size-4" />
			Aucun article. Importe ou ajoute des flux depuis <a href="/feeds" class="underline">Mes flux</a>.
		</p>
	{:else}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each articles as article, index (article.id)}
				<ArticleCard
					href="/articles/{article.id}"
					title={article.title}
					summary={article.summary}
					imageUrl={article.image_url}
					sourceLabel={article.source_label}
					publishedAt={article.published_at}
					accentHue={accentHueForFeed(article.feed_id)}
					featured={index === 0}
				/>
			{/each}
		</div>
	{/if}
</div>
