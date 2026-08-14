<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { Button } from '@lumia/ui';
	import Star from '@lucide/svelte/icons/star';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import ArticleGrid from '$domain/article/article-grid.svelte';

	const PAGE_SIZE = 24;

	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let loadingMore = $state(false);
	let hasMore = $state(false);
	let error = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			const loaded = await lumia.recommendation.getFavorites(PAGE_SIZE, 0);
			articles = loaded;
			hasMore = loaded.length === PAGE_SIZE;
		} catch {
			error = 'Impossible de charger tes favoris.';
		} finally {
			loading = false;
		}
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;
		try {
			const next = await lumia.recommendation.getFavorites(PAGE_SIZE, articles.length);
			articles = [...articles, ...next];
			hasMore = next.length === PAGE_SIZE;
		} catch {
			error = 'Impossible de charger la suite.';
		} finally {
			loadingMore = false;
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
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
		<p role="alert" class="text-sm text-destructive">{error}</p>
	{/if}

	<ArticleGrid {articles} {loading}>
		{#snippet empty()}
			<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
				<p class="text-sm text-muted-foreground">
					Rien pour le moment — marque un article en favori depuis sa page ou en le swipant.
				</p>
				<Button size="sm" href="{base}/articles">Parcourir les articles</Button>
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
</div>
