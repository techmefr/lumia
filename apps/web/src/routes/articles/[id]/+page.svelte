<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { sanitizeArticleHtml, type ArticleDetail } from '@lumia/core';
	import { Button, Card, CardContent } from '@lumia/ui';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';

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

<div class="mx-auto flex max-w-2xl flex-col gap-4">
	<a
		href="/articles"
		class="flex w-fit items-center gap-1 text-sm text-muted-foreground transition-transform hover:-translate-x-0.5 hover:text-foreground hover:underline"
	>
		<ArrowLeft class="size-4" />
		Retour aux articles
	</a>

	{#if loading}
		<p class="text-sm text-muted-foreground">Chargement…</p>
	{:else if error}
		<p class="text-sm text-destructive">{error}</p>
	{:else if article}
		<Card class="animate-in fade-in slide-in-from-bottom-2 duration-300">
			<CardContent class="pt-6">
				<h1 class="font-serif text-2xl font-semibold">{article.title}</h1>
				<a
					href={article.url}
					target="_blank"
					rel="noopener"
					class="flex w-fit items-center gap-1 text-sm text-primary hover:underline"
				>
					<ExternalLink class="size-3.5" />
					Lire la source
				</a>
				<div class="prose prose-sm mt-4 max-w-none">
					{@html sanitizeArticleHtml(article.content)}
				</div>
			</CardContent>
		</Card>

		<div class="flex gap-2">
			<Button
				variant={feedbackSent === 'like' ? 'default' : 'outline'}
				onclick={() => vote('like')}
			>
				<ThumbsUp class="size-4" /> J'aime
			</Button>
			<Button
				variant={feedbackSent === 'dislike' ? 'default' : 'outline'}
				onclick={() => vote('dislike')}
			>
				<ThumbsDown class="size-4" /> Je n'aime pas
			</Button>
			<Button
				variant={feedbackSent === 'save' ? 'default' : 'outline'}
				onclick={() => vote('save')}
			>
				<Bookmark class="size-4" /> Enregistrer
			</Button>
		</div>
	{/if}
</div>
