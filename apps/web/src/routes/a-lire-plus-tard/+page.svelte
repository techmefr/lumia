<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, toast } from '@lumia/ui';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import Plus from '@lucide/svelte/icons/plus';
	import CloudDownload from '@lucide/svelte/icons/cloud-download';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import ArticleGrid from '$domain/article/article-grid.svelte';
	import OfflineStorageIndicator from '$domain/offline/offline-storage-indicator.svelte';
	import { offlineLibrary } from '$technical/offline/offline-runtime';
	import { OfflineQuotaExceededError } from '$domain/offline/offline-library.svelte';

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
	let pendingOfflineIds = $state<string[]>([]);
	let makingAllAvailable = $state(false);

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

	async function toggleOffline(articleId: string) {
		if (pendingOfflineIds.includes(articleId)) return;
		pendingOfflineIds = [...pendingOfflineIds, articleId];
		try {
			if (offlineLibrary.isOffline(articleId)) {
				await offlineLibrary.makeUnavailable(articleId);
				toast(t('offline.removedToast'));
				return;
			}
			const detail = await lumia.article.getArticle(articleId);
			await offlineLibrary.makeAvailable(detail);
			toast(t('offline.addedToast'));
		} catch (cause) {
			toast(cause instanceof OfflineQuotaExceededError ? t('offline.quotaExceededToast') : t('offline.addFailedToast'));
		} finally {
			pendingOfflineIds = pendingOfflineIds.filter((id) => id !== articleId);
		}
	}

	async function makeAllAvailable() {
		if (makingAllAvailable) return;
		makingAllAvailable = true;
		try {
			const result = await offlineLibrary.makeAllAvailable(articles, (articleId) =>
				lumia.article.getArticle(articleId)
			);
			toast(
				result.skipped.length > 0
					? t('offline.makeAllPartial', { cached: result.cached.length, skipped: result.skipped.length })
					: t('offline.makeAllDone', { count: result.cached.length })
			);
		} finally {
			makingAllAvailable = false;
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
		void offlineLibrary.init();
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 data-test-page="read-later" class="flex items-center gap-2 text-2xl font-semibold">
			<Bookmark class="size-6 text-primary" />
			{t('readLater.title')}
		</h1>
		<p class="text-sm text-muted-foreground">{t('readLater.intro')}</p>
	</div>

	<Card>
		<CardHeader>
			<CardTitle>{t('offline.title')}</CardTitle>
			<CardDescription>{t('offline.description')}</CardDescription>
		</CardHeader>
		<CardContent class="flex flex-col gap-3">
			<OfflineStorageIndicator
				bytesUsed={offlineLibrary.bytesUsed}
				capBytes={offlineLibrary.capBytes}
				articleCount={offlineLibrary.records.length}
			/>
			<Button
				data-test-make-all-offline
				size="sm"
				variant="outline"
				class="w-fit"
				disabled={makingAllAvailable || articles.length === 0}
				onclick={makeAllAvailable}
			>
				<CloudDownload class="size-4" />
				{makingAllAvailable ? t('offline.makingAllAvailable') : t('offline.makeAllAvailable')}
			</Button>
		</CardContent>
	</Card>

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
					<Plus class="size-4" />
					{savingUrl ? t('readLater.extracting') : t('common.save')}
				</Button>
			</form>
		</CardContent>
	</Card>

	{#if error}
		<p data-test-list-error role="alert" class="text-sm text-destructive">{t(error)}</p>
	{/if}

	<ArticleGrid
		{articles}
		{loading}
		offlineControl
		offlineIds={offlineLibrary.offlineIds}
		offlinePendingIds={pendingOfflineIds}
		onToggleOffline={toggleOffline}
	>
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
