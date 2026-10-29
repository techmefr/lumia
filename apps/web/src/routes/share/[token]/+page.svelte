<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { sanitizeArticleHtml, type PublicArticle } from '@lumia/core';
	import { Skeleton } from '@lumia/ui';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Printer from '@lucide/svelte/icons/printer';
	import { lumia } from '$technical/api/client';
	import { safeHttpHref } from '$technical/url/safe-href';
	import { getLocale, t } from '$technical/i18n/i18n.svelte';
	import { formatDateInUserTimezone } from '$technical/time/format-date';

	let article = $state<PublicArticle | null>(null);
	let loading = $state(true);
	let missing = $state(false);

	onMount(() => {
		const token = page.params.token;
		if (!token) {
			missing = true;
			loading = false;
			return;
		}
		lumia.article
			.getPublicArticle(token)
			.then((loaded) => (article = loaded))
			.catch(() => (missing = true))
			.finally(() => (loading = false));
	});
</script>

<!-- Both meta tags are about a page that has no business being found or leaking where it was read
     from; the backend answers with the same intent in headers, for clients that skip the markup. -->
<svelte:head>
	<title>{article?.title ?? 'Lumia'}</title>
	<meta name="robots" content="noindex, nofollow, noarchive" />
	<meta name="referrer" content="no-referrer" />
</svelte:head>

<div class="mx-auto flex w-full flex-col gap-4 py-2">
	{#if loading}
		<div role="status" aria-label={t('publicShare.loading')} class="flex flex-col gap-3">
			<Skeleton class="h-8 w-3/4" />
			<Skeleton class="h-4 w-40" />
			{#each Array(6)}
				<Skeleton class="h-4 w-full" />
			{/each}
		</div>
	{:else if missing || !article}
		<p data-test-public-missing role="alert" class="text-sm text-destructive">
			{t('publicShare.notFound')}
		</p>
	{:else}
		<article lang={article.language} data-test-public-article>
			{#if article.image_url}
				<img
					src={article.image_url}
					alt=""
					referrerpolicy="no-referrer"
					class="mb-4 max-h-96 w-full rounded-2xl object-cover print:max-h-none"
				/>
			{/if}
			<h1 data-test-public-title class="font-serif text-2xl font-semibold sm:text-3xl">
				{article.title}
			</h1>
			<p class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
				<time datetime={article.published_at}>
					{formatDateInUserTimezone(article.published_at, getLocale())}
				</time>
				{#if article.author_name}
					<span>{t('publicShare.by', { author: article.author_name })}</span>
				{/if}
				<span data-test-public-notice>{t('publicShare.notice')}</span>
			</p>
			<p class="mt-2 flex flex-wrap items-center gap-3 text-sm print:hidden">
				<a
					data-test-public-source
					href={safeHttpHref(article.url)}
					target="_blank"
					rel="noopener noreferrer nofollow"
					class="flex w-fit items-center gap-1 text-primary hover:underline"
				>
					<ExternalLink class="size-3.5" aria-hidden="true" />
					{t('publicShare.readSource')}
				</a>
				<button
					type="button"
					data-test-print-button
					onclick={() => window.print()}
					class="flex items-center gap-1.5 rounded-md px-2 py-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
				>
					<Printer class="size-4" aria-hidden="true" />
					{t('print.button')}
				</button>
			</p>
			<p class="mt-2 hidden break-all text-sm print:block">
				{t('print.sourceLabel')}
				{article.url}
			</p>
			<div data-test-public-content class="prose prose-base mt-4">
				{@html sanitizeArticleHtml(article.content)}
			</div>
		</article>
	{/if}
</div>
