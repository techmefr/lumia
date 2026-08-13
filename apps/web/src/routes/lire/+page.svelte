<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { ArticleSummary } from '@lumia/core';
	import Shuffle from '@lucide/svelte/icons/shuffle';
	import Inbox from '@lucide/svelte/icons/inbox';
	import PartyPopper from '@lucide/svelte/icons/party-popper';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import SwipeStack from '$domain/article/swipe-stack.svelte';

	let articles = $state<ArticleSummary[]>([]);
	let remaining = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let label = $state<string | null>(null);

	function vote(article: ArticleSummary, choice: 'like' | 'dislike') {
		void lumia.recommendation.sendFeedback(article.id, { sentiment: choice });
		remaining = remaining.filter((a) => a.id !== article.id);
	}

	function save(article: ArticleSummary) {
		void lumia.recommendation.sendFeedback(article.id, { saved: true });
	}

	function favorite(article: ArticleSummary) {
		void lumia.recommendation.sendFeedback(article.id, { favorite: true });
	}

	onMount(() => {
		if (!requireAuth()) return;
		const params = page.url.searchParams;
		const folderId = params.get('folder_id') ?? undefined;
		const feedId = params.get('feed_id') ?? undefined;
		label = params.get('label');

		lumia.article
			.listArticles({ folderId, feedId })
			.then((loaded) => {
				articles = loaded;
				remaining = loaded;
			})
			.catch(() => (error = 'Impossible de charger les articles.'))
			.finally(() => (loading = false));
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Shuffle class="size-6 text-primary" />
			Lecture{label ? ` — ${label}` : ''}
		</h1>
		<p class="text-sm text-muted-foreground">
			Glisse à droite pour aimer, à gauche pour passer — enregistre ou mets en favoris sans quitter la carte.
		</p>
	</div>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{error}</p>
	{/if}

	{#if loading}
		<p role="status" class="text-sm text-muted-foreground">Chargement…</p>
	{:else if articles.length === 0}
		<p class="flex items-center gap-2 text-sm text-muted-foreground">
			<Inbox class="size-4" />
			Aucun article ici pour le moment.
		</p>
	{:else if remaining.length === 0}
		<div class="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
			<PartyPopper class="size-8 text-primary" />
			<p class="font-medium">Tu as tout lu pour l'instant.</p>
		</div>
	{:else}
		<SwipeStack
			articles={remaining}
			onLike={(article) => vote(article, 'like')}
			onDislike={(article) => vote(article, 'dislike')}
			onSave={save}
			onFavorite={favorite}
			onOpen={(article) => goto(`/articles/${article.id}`)}
		/>
	{/if}
</div>
