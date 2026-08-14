<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { ArticleSummary } from '@lumia/core';
	import Shuffle from '@lucide/svelte/icons/shuffle';
	import Inbox from '@lucide/svelte/icons/inbox';
	import PartyPopper from '@lucide/svelte/icons/party-popper';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import SwipeStack from '$domain/article/swipe-stack.svelte';

	let articles = $state<ArticleSummary[]>([]);
	let remaining = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
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
			.catch(() => (error = 'read.loadFailed'))
			.finally(() => (loading = false));
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Shuffle class="size-6 text-primary" />
			{label ? t('read.titleWithLabel', { label }) : t('read.title')}
		</h1>
		<p class="text-sm text-muted-foreground">{t('read.help')}</p>
	</div>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{t(error)}</p>
	{/if}

	{#if loading}
		<p role="status" class="text-sm text-muted-foreground">{t('common.loading')}</p>
	{:else if articles.length === 0}
		<p class="flex items-center gap-2 text-sm text-muted-foreground">
			<Inbox class="size-4" />
			{t('read.empty')}
		</p>
	{:else if remaining.length === 0}
		<div class="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
			<PartyPopper class="size-8 text-primary" />
			<p class="font-medium">{t('read.allRead')}</p>
		</div>
	{:else}
		<SwipeStack
			articles={remaining}
			onLike={(article) => vote(article, 'like')}
			onDislike={(article) => vote(article, 'dislike')}
			onSave={save}
			onFavorite={favorite}
			onOpen={(article) => goto(`${base}/articles/${article.id}`)}
		/>
	{/if}
</div>
