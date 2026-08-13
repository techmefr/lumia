<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { lumia } from '$lib/client';
	import { requireAuth } from '$lib/require-auth';

	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(() => {
		if (!requireAuth()) return;
		lumia.recommendation
			.getEtincelle()
			.then((loaded) => (articles = loaded))
			.catch(() => (error = "Impossible de charger l'Étincelle."))
			.finally(() => (loading = false));
	});
</script>

<h1>L'Étincelle</h1>
<p>Une sélection apprise à partir de tes retours.</p>

{#if error}
	<p class="error">{error}</p>
{/if}

{#if loading}
	<p>Chargement…</p>
{:else if articles.length === 0}
	<p>Pas encore assez de retours pour te faire une sélection — like/dislike des articles pour l'entraîner.</p>
{:else}
	<ul>
		{#each articles as article (article.id)}
			<li>
				<a href="/articles/{article.id}">{article.title}</a>
				{#if article.summary}<p>{article.summary}</p>{/if}
			</li>
		{/each}
	</ul>
{/if}

<style>
	ul {
		list-style: none;
		padding: 0;
	}
	li {
		padding: 0.75rem 0;
		border-bottom: 1px solid #eee;
	}
	.error {
		color: #c0392b;
	}
</style>
