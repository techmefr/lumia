<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary, Feed } from '@lumia/core';
	import { ArticleCard } from '@lumia/ui';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { accentHueForFeed } from '$domain/article/accent-hue';

	let articles = $state<ArticleSummary[]>([]);
	let feeds = $state<Feed[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	function feedTitle(feedId: string): string {
		return feeds.find((feed) => feed.id === feedId)?.title ?? 'Flux';
	}

	onMount(() => {
		if (!requireAuth()) return;
		void lumia.feed.listFeeds().then((loaded) => (feeds = loaded));
		lumia.recommendation
			.getEtincelle()
			.then((loaded) => (articles = loaded))
			.catch(() => (error = "Impossible de charger l'Étincelle."))
			.finally(() => (loading = false));
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="text-2xl font-semibold">L'Étincelle</h1>
		<p class="text-sm text-muted-foreground">Une sélection apprise à partir de tes retours.</p>
	</div>

	{#if error}
		<p class="text-sm text-destructive">{error}</p>
	{/if}

	{#if loading}
		<p class="text-sm text-muted-foreground">Chargement…</p>
	{:else if articles.length === 0}
		<p class="text-sm text-muted-foreground">
			Pas encore assez de retours pour te faire une sélection — like/dislike des articles pour l'entraîner.
		</p>
	{:else}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each articles as article (article.id)}
				<ArticleCard
					href="/articles/{article.id}"
					title={article.title}
					summary={article.summary}
					sourceLabel={feedTitle(article.feed_id)}
					publishedAt={article.published_at}
					accentHue={accentHueForFeed(article.feed_id)}
				/>
			{/each}
		</div>
	{/if}
</div>
