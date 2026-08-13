<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary, Feed } from '@lumia/core';
	import { ArticleCard } from '@lumia/ui';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import Inbox from '@lucide/svelte/icons/inbox';
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
			.getSaved()
			.then((loaded) => (articles = loaded))
			.catch(() => (error = 'Impossible de charger ta liste de lecture.'))
			.finally(() => (loading = false));
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Bookmark class="size-6 text-primary" />
			À lire plus tard
		</h1>
		<p class="text-sm text-muted-foreground">
			Les articles que tu as enregistrés depuis le bouton « Enregistrer ».
		</p>
	</div>

	{#if error}
		<p class="text-sm text-destructive">{error}</p>
	{/if}

	{#if loading}
		<p class="text-sm text-muted-foreground">Chargement…</p>
	{:else if articles.length === 0}
		<p class="flex items-center gap-2 text-sm text-muted-foreground">
			<Inbox class="size-4" />
			Rien pour le moment — enregistre un article depuis sa page pour le retrouver ici.
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
