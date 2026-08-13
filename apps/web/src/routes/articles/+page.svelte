<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary, Feed, Folder } from '@lumia/core';
	import { ArticleCard } from '@lumia/ui';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Inbox from '@lucide/svelte/icons/inbox';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { accentHueForFeed } from '$domain/article/accent-hue';

	let articles = $state<ArticleSummary[]>([]);
	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let selectedFolderId = $state('');
	let selectedFeedId = $state('');
	let loading = $state(true);
	let error = $state<string | null>(null);

	function feedTitle(feedId: string): string {
		return feeds.find((feed) => feed.id === feedId)?.title ?? 'Flux';
	}

	async function loadArticles() {
		loading = true;
		error = null;
		try {
			articles = await lumia.article.listArticles({
				folderId: selectedFolderId || undefined,
				feedId: selectedFeedId || undefined
			});
		} catch {
			error = 'Impossible de charger les articles.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		if (!requireAuth()) return;
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
			{#each articles as article (article.id)}
				<ArticleCard
					href="/articles/{article.id}"
					title={article.title}
					summary={article.summary}
					imageUrl={article.image_url}
					sourceLabel={feedTitle(article.feed_id)}
					publishedAt={article.published_at}
					accentHue={accentHueForFeed(article.feed_id)}
				/>
			{/each}
		</div>
	{/if}
</div>
