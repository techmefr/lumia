<script lang="ts">
	import { base } from '$technical/paths/base';
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, toast, Icon } from '@lumia/ui';
	import { Add01Icon, Bookmark01Icon } from '@hugeicons/core-free-icons';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import { readSavedList } from '$technical/offline/offline-reads';
	import ArticleGrid from '$domain/article/article-grid.svelte';

	const PAGE_SIZE = 24;

	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let loadingMore = $state(false);
	let hasMore = $state(false);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
	let newUrl = $state('');
	let savingUrl = $state(false);
	let offline = $state(false);
	let saveError = $state<MessageKey | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			const listing = await readSavedList(() => lumia.recommendation.getSaved(PAGE_SIZE, 0));
			articles = listing.articles;
			offline = listing.offline;
			hasMore = !listing.offline && listing.articles.length === PAGE_SIZE;
		} catch {
			error = 'readLater.loadFailed';
		} finally {
			loading = false;
		}
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;
		try {
			const next = await lumia.recommendation.getSaved(PAGE_SIZE, articles.length);
			articles = [...articles, ...next];
			hasMore = next.length === PAGE_SIZE;
		} catch {
			error = 'common.loadMoreFailed';
		} finally {
			loadingMore = false;
		}
	}

	async function saveUrl(event: SubmitEvent) {
		event.preventDefault();
		const url = newUrl.trim();
		if (!url) return;

		savingUrl = true;
		saveError = null;
		try {
			const saved = await lumia.article.saveUrl(url);
			newUrl = '';
			await load();
			toast(t('readLater.savedToast', { title: saved.title }));
		} catch {
			saveError = 'readLater.saveFailed';
		} finally {
			savingUrl = false;
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 data-test-page="read-later" class="flex items-center gap-2 text-2xl font-semibold">
			<Icon icon={Bookmark01Icon} class="size-6 text-primary" />
			{t('readLater.title')}
		</h1>
		<p class="text-sm text-muted-foreground">{t('readLater.intro')}</p>
	</div>

	<Card>
		<CardHeader>
			<CardTitle>{t('readLater.saveTitle')}</CardTitle>
			<CardDescription>{t('readLater.saveDescription')}</CardDescription>
		</CardHeader>
		<CardContent>
			{#if saveError}
				<p data-test-save-error role="alert" class="mb-2 text-sm text-destructive">{t(saveError)}</p>
			{/if}
			<form data-test-save-url-form class="flex flex-wrap items-end gap-2" onsubmit={saveUrl}>
				<div class="flex max-w-sm flex-1 flex-col gap-1.5">
					<Label for="save-url">{t('readLater.urlLabel')}</Label>
					<Input
						id="save-url"
						type="url"
						bind:value={newUrl}
						placeholder={t('readLater.urlPlaceholder')}
						required
						disabled={savingUrl}
					/>
				</div>
				<Button type="submit" disabled={savingUrl}>
					<Icon icon={Add01Icon} class="size-4" />
					{savingUrl ? t('readLater.extracting') : t('common.save')}
				</Button>
			</form>
		</CardContent>
	</Card>

	{#if offline}
		<p data-test-offline-list-notice role="status" class="text-sm text-muted-foreground">
			{t('offline.listNotice', { count: articles.length })}
		</p>
	{/if}

	{#if error}
		<p data-test-list-error role="alert" class="text-sm text-destructive">{t(error)}</p>
	{/if}

	<ArticleGrid {articles} {loading}>
		{#snippet empty()}
			<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
				<p class="text-sm text-muted-foreground">{t('readLater.empty')}</p>
				<Button size="sm" href="{base}/articles">{t('common.browseArticles')}</Button>
			</div>
		{/snippet}

		{#snippet footer()}
			{#if hasMore}
				<div class="mt-6 flex justify-center">
					<Button data-test-load-more variant="outline" onclick={loadMore} disabled={loadingMore}>
						{loadingMore ? t('common.loading') : t('common.loadMore')}
					</Button>
				</div>
			{/if}
		{/snippet}
	</ArticleGrid>
</div>
