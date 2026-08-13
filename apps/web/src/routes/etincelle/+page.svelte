<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { ArticleSummary } from '@lumia/core';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Inbox from '@lucide/svelte/icons/inbox';
	import PartyPopper from '@lucide/svelte/icons/party-popper';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import SwipeStack from '$domain/article/swipe-stack.svelte';

	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let remaining = $state<ArticleSummary[]>([]);

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
		lumia.recommendation
			.getEtincelle()
			.then((loaded) => {
				articles = loaded;
				remaining = loaded;
			})
			.catch(() => (error = "Impossible de charger l'Étincelle."))
			.finally(() => (loading = false));
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Sparkles class="size-6 text-primary" />
			L'Étincelle
		</h1>
		<p class="text-sm text-muted-foreground">
			Glisse à droite pour aimer, à gauche pour passer — ou touche la carte pour l'ouvrir.
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
			Pas encore assez de retours pour te faire une sélection — like/dislike des articles pour l'entraîner.
		</p>
	{:else if remaining.length === 0}
		<div class="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
			<PartyPopper class="size-8 text-primary" />
			<p class="font-medium">Tu as tout vu pour l'instant.</p>
			<p class="text-sm">Reviens plus tard pour une nouvelle sélection.</p>
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
