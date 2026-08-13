<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { sanitizeArticleHtml, type ArticleDetail } from '@lumia/core';
	import { Button, Card, CardContent, Badge } from '@lumia/ui';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Tag from '@lucide/svelte/icons/tag';
	import Share2 from '@lucide/svelte/icons/share-2';
	import Check from '@lucide/svelte/icons/check';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';

	let article = $state<ArticleDetail | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let feedbackSent = $state<string | null>(null);
	let linkCopied = $state(false);

	async function vote(choice: 'like' | 'dislike' | 'save') {
		if (!article) return;
		await lumia.recommendation.sendFeedback(article.id, choice);
		feedbackSent = choice;
	}

	async function share() {
		if (!article) return;
		if (navigator.share) {
			try {
				await navigator.share({ title: article.title, url: article.url });
				return;
			} catch {
				return;
			}
		}
		await navigator.clipboard.writeText(article.url);
		linkCopied = true;
		setTimeout(() => (linkCopied = false), 2000);
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

<div class="mx-auto flex w-full flex-col gap-4 pb-24">
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
		<Card class="animate-in overflow-hidden fade-in zoom-in-95 slide-in-from-bottom-3 duration-500 ease-out">
			{#if article.image_url}
				<div class="overflow-hidden" style={`view-transition-name: article-image-${article.id};`}>
					<img
						src={article.image_url}
						alt=""
						class="h-72 w-full animate-in scale-100 object-cover fade-in zoom-in-110 duration-700 ease-out sm:h-96"
						loading="lazy"
					/>
				</div>
			{/if}
			<CardContent class="pt-6">
				<h1 class="animate-in font-serif text-2xl font-semibold fade-in slide-in-from-bottom-1 duration-500 sm:text-3xl">
					{article.title}
				</h1>
				<div class="flex items-center justify-between">
					<a
						href={article.url}
						target="_blank"
						rel="noopener"
						class="flex w-fit items-center gap-1 text-sm text-primary hover:underline"
					>
						<ExternalLink class="size-3.5" />
						Lire la source
					</a>
					<button
						onclick={share}
						class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
					>
						{#if linkCopied}
							<Check class="size-4 text-primary" />
							Lien copié
						{:else}
							<Share2 class="size-4" />
							Partager
						{/if}
					</button>
				</div>

				<div class="mt-3 flex flex-wrap items-center gap-1.5">
					<a href="/articles?feed_id={article.feed_id}">
						<Badge variant="secondary" class="transition-transform hover:-translate-y-0.5">
							{article.source_label}
						</Badge>
					</a>
					{#if article.author_id && article.author_name}
						<a
							href="/articles?author_id={article.author_id}&author_name={encodeURIComponent(
								article.author_name
							)}"
						>
							<Badge variant="outline" class="transition-transform hover:-translate-y-0.5">
								{article.author_name}
							</Badge>
						</a>
					{/if}
					{#if article.category_id && article.category_name}
						<a
							href="/articles?category_id={article.category_id}&category_name={encodeURIComponent(
								article.category_name
							)}"
						>
							<Badge variant="outline" class="transition-transform hover:-translate-y-0.5">
								{article.category_name}
							</Badge>
						</a>
					{/if}
					{#each article.keywords as keyword (keyword.id)}
						<a
							href="/articles?keyword_id={keyword.id}&keyword_term={encodeURIComponent(
								keyword.term
							)}"
						>
							<Badge
								variant="outline"
								class="flex items-center gap-1 transition-transform hover:-translate-y-0.5"
							>
								<Tag class="size-3" />
								{keyword.term}
							</Badge>
						</a>
					{/each}
				</div>

				<div class="prose prose-base mt-4 max-w-none">
					{@html sanitizeArticleHtml(article.content)}
				</div>
			</CardContent>
		</Card>

		<div
			class="fixed inset-x-0 z-40 flex justify-center border-t bg-background/90 p-3 backdrop-blur"
			style="bottom: var(--bottom-nav-h, 0px)"
		>
			<div class="flex w-full max-w-3xl gap-2">
				<Button
					class="flex-1"
					variant={feedbackSent === 'like' ? 'default' : 'outline'}
					onclick={() => vote('like')}
				>
					<ThumbsUp class="size-4" /> J'aime
				</Button>
				<Button
					class="flex-1"
					variant={feedbackSent === 'dislike' ? 'default' : 'outline'}
					onclick={() => vote('dislike')}
				>
					<ThumbsDown class="size-4" /> Je n'aime pas
				</Button>
				<Button
					class="flex-1"
					variant={feedbackSent === 'save' ? 'default' : 'outline'}
					onclick={() => vote('save')}
				>
					<Bookmark class="size-4" /> Enregistrer
				</Button>
			</div>
		</div>
	{/if}
</div>
