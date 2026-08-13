<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { ArticleCard } from '@lumia/ui';
	import Star from '@lucide/svelte/icons/star';
	import Inbox from '@lucide/svelte/icons/inbox';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { accentHueForFeed } from '$domain/article/accent-hue';

	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(() => {
		if (!requireAuth()) return;
		lumia.recommendation
			.getFavorites()
			.then((loaded) => (articles = loaded))
			.catch(() => (error = 'Impossible de charger tes favoris.'))
			.finally(() => (loading = false));
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Star class="size-6 text-primary" />
			Favoris
		</h1>
		<p class="text-sm text-muted-foreground">
			Tes articles marqués en favoris, à retrouver ici pour une veille par thème.
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
			Rien pour le moment — marque un article en favori depuis sa page ou en le swipant.
		</p>
	{:else}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each articles as article, index (article.id)}
				<ArticleCard
					id={article.id}
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
