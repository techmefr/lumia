<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { ArticleSummary } from '@lumia/core';
	import { Button, Skeleton, toast } from '@lumia/ui';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Inbox from '@lucide/svelte/icons/inbox';
	import PartyPopper from '@lucide/svelte/icons/party-popper';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import SwipeStack from '$domain/article/swipe-stack.svelte';

	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
	let remaining = $state<ArticleSummary[]>([]);

	function vote(article: ArticleSummary, choice: 'like' | 'dislike') {
		void lumia.recommendation.sendFeedback(article.id, { sentiment: choice });
		remaining = remaining.filter((a) => a.id !== article.id);
	}

	function save(article: ArticleSummary) {
		void lumia.recommendation.sendFeedback(article.id, { saved: true });
		toast(t('etincelle.savedToast'));
	}

	function favorite(article: ArticleSummary) {
		void lumia.recommendation.sendFeedback(article.id, { favorite: true });
		toast(t('etincelle.favoriteToast'));
	}

	onMount(() => {
		if (!requireAuth()) return;
		lumia.recommendation
			.getEtincelle()
			.then((loaded) => {
				articles = loaded;
				remaining = loaded;
			})
			.catch(() => (error = 'etincelle.loadFailed'))
			.finally(() => (loading = false));
	});
</script>

<div class="flex flex-col gap-4">
	<div>
		<h1 data-test-page="etincelle" class="flex items-center gap-2 text-2xl font-semibold">
			<Sparkles class="size-6 text-primary" />
			{t('etincelle.title')}
		</h1>
		<p class="sr-only text-sm text-muted-foreground sm:not-sr-only">{t('etincelle.help')}</p>
	</div>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{t(error)}</p>
	{/if}

	{#if loading}
		<div role="status" aria-label={t('etincelle.loading')} class="flex justify-center">
			<Skeleton
				class="h-[calc(100dvh-22rem)] max-h-[40rem] min-h-[22rem] w-full max-w-lg rounded-3xl sm:h-[calc(100dvh-20rem)]"
			/>
		</div>
	{:else if articles.length === 0}
		<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
			<p class="flex items-center gap-2 text-sm text-muted-foreground">
				<Inbox class="size-4" />
				{t('etincelle.notEnough')}
			</p>
			<Button size="sm" href="{base}/articles">{t('common.browseArticles')}</Button>
		</div>
	{:else if remaining.length === 0}
		<div class="flex flex-col items-center gap-2 py-16 text-center text-muted-foreground">
			<PartyPopper class="size-8 text-primary" />
			<p class="font-medium">{t('etincelle.allSeen')}</p>
			<p class="text-sm">{t('etincelle.comeBack')}</p>
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
