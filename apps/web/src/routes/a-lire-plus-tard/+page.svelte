<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, toast } from '@lumia/ui';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import Plus from '@lucide/svelte/icons/plus';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
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
	let saveError = $state<MessageKey | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			const loaded = await lumia.recommendation.getSaved(PAGE_SIZE, 0);
			articles = loaded;
			hasMore = loaded.length === PAGE_SIZE;
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
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Bookmark class="size-6 text-primary" />
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
				<p role="alert" class="mb-2 text-sm text-destructive">{t(saveError)}</p>
			{/if}
			<form class="flex flex-wrap items-end gap-2" onsubmit={saveUrl}>
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
					<Plus class="size-4" />
					{savingUrl ? t('readLater.extracting') : t('common.save')}
				</Button>
			</form>
		</CardContent>
	</Card>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{t(error)}</p>
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
					<Button variant="outline" onclick={loadMore} disabled={loadingMore}>
						{loadingMore ? t('common.loading') : t('common.loadMore')}
					</Button>
				</div>
			{/if}
		{/snippet}
	</ArticleGrid>
</div>
