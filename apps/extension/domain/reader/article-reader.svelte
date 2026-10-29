<script lang="ts">
	import type { ArticleDetail, LumiaClient } from '@lumia/core';
	import { sanitizeArticleHtml } from '@lumia/core';
	import { Button } from '@lumia/ui';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import { locale, t } from '$technical/i18n/i18n';
	import { isSessionLost } from './reader-session';
	import { isWebUrl } from './web-url';

	let {
		client,
		articleId,
		onsessionlost
	}: { client: LumiaClient; articleId: string; onsessionlost: () => void } = $props();

	let article = $state<ArticleDetail | null>(null);
	let failed = $state(false);

	const publishedOn = $derived(
		article ? new Date(article.published_at).toLocaleDateString(locale) : ''
	);

	async function load() {
		article = null;
		failed = false;
		try {
			article = await client.article.getArticle(articleId);
		} catch (error) {
			if (isSessionLost(error)) onsessionlost();
			failed = true;
			return;
		}
		void client.recommendation.markRead({ article_ids: [articleId], read: true }).catch(() => undefined);
	}

	$effect(() => {
		void articleId;
		void load();
	});
</script>

<article class="flex flex-col gap-3">
	<Button data-test-back variant="ghost" href="#" class="self-start">
		<ArrowLeft aria-hidden="true" />
		{t('reader.back')}
	</Button>

	{#if failed}
		<div class="flex flex-col items-start gap-2">
			<p data-test-article-error role="alert" class="text-sm text-destructive">
				{t('reader.articleFailed')}
			</p>
			<Button variant="outline" onclick={load}>{t('reader.retry')}</Button>
		</div>
	{:else if article === null}
		<p data-test-article-loading role="status" class="text-sm text-muted-foreground">
			{t('reader.loading')}
		</p>
	{:else}
		<header class="flex flex-col gap-1">
			<p class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
				{article.source_label} · {publishedOn}
			</p>
			<h2 data-test-article-title class="text-xl leading-snug">{article.title}</h2>
		</header>
		<div data-test-article-content class="reader-content">
			{@html sanitizeArticleHtml(article.content)}
		</div>
		{#if isWebUrl(article.url)}
			<Button
				data-test-open-original
				variant="outline"
				href={article.url}
				target="_blank"
				rel="noopener noreferrer"
			>
				<ExternalLink aria-hidden="true" />
				{t('reader.openOriginal')}
			</Button>
		{/if}
	{/if}
</article>
