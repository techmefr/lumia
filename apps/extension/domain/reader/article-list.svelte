<script lang="ts">
	import { untrack } from 'svelte';
	import type { ArticleSummary, Feed, LumiaClient } from '@lumia/core';
	import {
		accentHueForFeed,
		ArticleCard,
		ArticleCardSkeleton,
		Button,
		Label
	} from '@lumia/ui';
	import { locale, t } from '$technical/i18n/i18n';
	import { isSessionLost } from './reader-session';

	let { client, onsessionlost }: { client: LumiaClient; onsessionlost: () => void } = $props();

	const PAGE_SIZE = 20;
	const SKELETON_COUNT = 3;

	let feeds = $state<Feed[]>([]);
	let feedId = $state('');
	let unreadOnly = $state(false);
	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let failed = $state(false);
	let hasMore = $state(false);

	const cardLabels = {
		locale,
		readLabel: t('reader.read'),
		scoreTitle: t('reader.relevanceTitle'),
		scoreSuffix: t('reader.scoreSuffix'),
		minutesLabel: (minutes: number) => t('reader.minutes', { count: minutes })
	};

	async function fetchPage(offset: number): Promise<ArticleSummary[] | null> {
		try {
			return await client.article.listArticles({
				feedId: feedId || undefined,
				unreadOnly,
				limit: PAGE_SIZE,
				offset
			});
		} catch (error) {
			if (isSessionLost(error)) onsessionlost();
			return null;
		}
	}

	async function reload() {
		loading = true;
		failed = false;
		const page = await fetchPage(0);
		if (page === null) {
			articles = [];
			failed = true;
		} else {
			articles = page;
			hasMore = page.length === PAGE_SIZE;
		}
		loading = false;
	}

	async function loadMore() {
		loading = true;
		const page = await fetchPage(articles.length);
		if (page === null) {
			failed = true;
		} else {
			articles = [...articles, ...page];
			hasMore = page.length === PAGE_SIZE;
		}
		loading = false;
	}

	$effect(() => {
		void feedId;
		void unreadOnly;
		untrack(() => void reload());
	});

	$effect(() => {
		void client.feed
			.listFeeds()
			.then((list) => (feeds = list))
			.catch(() => (feeds = []));
	});
</script>

<div class="flex flex-col gap-3">
	<div class="flex flex-col gap-1.5">
		<Label for="feed-filter">{t('reader.feedFilter')}</Label>
		<select
			id="feed-filter"
			data-test-feed-filter
			bind:value={feedId}
			class="h-9 w-full rounded-md border border-input bg-background px-2 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
		>
			<option value="">{t('reader.allFeeds')}</option>
			{#each feeds as feed (feed.id)}
				<option value={feed.id}>{feed.title}</option>
			{/each}
		</select>
	</div>

	<label class="flex items-center gap-2 text-sm">
		<input data-test-unread-only type="checkbox" bind:checked={unreadOnly} />
		{t('reader.unreadOnly')}
	</label>

	{#if failed}
		<div class="flex flex-col items-start gap-2">
			<p data-test-list-error role="alert" class="text-sm text-destructive">
				{t('reader.loadFailed')}
			</p>
			<Button variant="outline" onclick={reload}>{t('reader.retry')}</Button>
		</div>
	{:else if loading && articles.length === 0}
		<div data-test-list-loading role="status" aria-label={t('reader.loading')} class="flex flex-col gap-3">
			{#each { length: SKELETON_COUNT } as _, index (index)}
				<ArticleCardSkeleton />
			{/each}
		</div>
	{:else if articles.length === 0}
		<p data-test-list-empty class="text-sm text-muted-foreground">{t('reader.empty')}</p>
	{:else}
		<ul class="flex flex-col gap-3">
			{#each articles as article (article.id)}
				<li>
					<ArticleCard
						id={article.id}
						href={`#article/${article.id}`}
						title={article.title}
						summary={article.summary}
						imageUrl={article.image_url}
						sourceLabel={article.source_label}
						publishedAt={article.published_at}
						accentHue={accentHueForFeed(article.feed_id)}
						readingMinutes={article.reading_minutes}
						read={article.read}
						scrollProgress={article.scroll_progress}
						relevanceScore={article.relevance_score}
						{...cardLabels}
					/>
				</li>
			{/each}
		</ul>
		{#if hasMore}
			<Button data-test-load-more variant="outline" disabled={loading} onclick={loadMore}>
				{loading ? t('reader.loading') : t('reader.loadMore')}
			</Button>
		{/if}
	{/if}
</div>
