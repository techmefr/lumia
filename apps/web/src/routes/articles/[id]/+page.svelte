<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { sanitizeArticleHtml, type ArticleDetail } from '@lumia/core';
	import { lumia } from '$lib/client';
	import { requireAuth } from '$lib/require-auth';

	let article = $state<ArticleDetail | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let feedbackSent = $state<string | null>(null);

	async function vote(choice: 'like' | 'dislike' | 'save') {
		if (!article) return;
		await lumia.recommendation.sendFeedback(article.id, choice);
		feedbackSent = choice;
	}

	onMount(() => {
		if (!requireAuth()) return;
		const articleId = page.params.id;
		if (!articleId) {
			error = 'Article introuvable.';
			loading = false;
			return;
		}
		lumia.article
			.getArticle(articleId)
			.then((loaded) => (article = loaded))
			.catch(() => (error = 'Article introuvable.'))
			.finally(() => (loading = false));
	});
</script>

<p><a href="/articles">← Retour aux articles</a></p>

{#if loading}
	<p>Chargement…</p>
{:else if error}
	<p class="error">{error}</p>
{:else if article}
	<article>
		<h1>{article.title}</h1>
		<p><a href={article.url} target="_blank" rel="noopener">Lire la source</a></p>
		<div class="content">{@html sanitizeArticleHtml(article.content)}</div>
	</article>

	<div class="feedback">
		<button onclick={() => vote('like')} disabled={feedbackSent === 'like'}>J'aime</button>
		<button onclick={() => vote('dislike')} disabled={feedbackSent === 'dislike'}>Je n'aime pas</button>
		<button onclick={() => vote('save')} disabled={feedbackSent === 'save'}>Enregistrer</button>
	</div>
{/if}

<style>
	.error {
		color: #c0392b;
	}
	.feedback {
		display: flex;
		gap: 0.5rem;
		margin-top: 1.5rem;
	}
</style>
