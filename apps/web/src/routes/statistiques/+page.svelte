<script lang="ts">
	import { onMount } from 'svelte';
	import type { Popularity, ReadingStatistics } from '@lumia/core';
	import { Button } from '@lumia/ui';
	import ChartColumn from '@lucide/svelte/icons/chart-column';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import DailyBars from '$domain/statistics/daily-bars.svelte';
	import FeedEngagementTable from '$domain/statistics/feed-engagement-table.svelte';
	import RankedBars from '$domain/statistics/ranked-bars.svelte';

	const PERIODS = [7, 30, 90];

	let days = $state(30);
	let stats = $state<ReadingStatistics | null>(null);
	let popularity = $state<Popularity | null>(null);
	let loading = $state(true);
	let error = $state<MessageKey | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			const [reading, popular] = await Promise.all([
				lumia.recommendation.getReadingStatistics(days),
				lumia.recommendation.getPopularArticles(Math.min(days, 90))
			]);
			stats = reading;
			popularity = popular;
		} catch {
			error = 'stats.loadFailed';
		} finally {
			loading = false;
		}
	}

	function choosePeriod(period: number) {
		if (period === days) return;
		days = period;
		void load();
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<ChartColumn class="size-6 text-primary" />
			{t('stats.title')}
		</h1>
		<p class="text-sm text-muted-foreground">{t('stats.intro')}</p>
	</div>

	<div role="group" aria-label={t('stats.period')} class="flex gap-2">
		{#each PERIODS as period (period)}
			<Button
				data-test-period={period}
				size="sm"
				variant={period === days ? 'default' : 'outline'}
				aria-pressed={period === days}
				onclick={() => choosePeriod(period)}
			>
				{t('stats.days', { count: period })}
			</Button>
		{/each}
	</div>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{t(error)}</p>
	{/if}

	{#if loading && !stats}
		<p data-test-loading class="text-sm text-muted-foreground" role="status">
			{t('common.loading')}
		</p>
	{:else if stats}
		<div aria-busy={loading} class="flex flex-col gap-6">
			<dl class="grid grid-cols-2 gap-4 sm:grid-cols-4">
				<div class="rounded-2xl border p-4">
					<dt class="text-xs text-muted-foreground">{t('stats.articlesRead')}</dt>
					<dd data-test-articles-read class="text-2xl font-semibold tabular-nums">
						{stats.articles_read}
					</dd>
				</div>
				<div class="rounded-2xl border p-4">
					<dt class="text-xs text-muted-foreground">{t('stats.readingTime')}</dt>
					<dd data-test-reading-time class="text-2xl font-semibold tabular-nums">
						{t('common.minutes', { count: stats.reading_minutes })}
					</dd>
				</div>
				<div class="rounded-2xl border p-4">
					<dt class="text-xs text-muted-foreground">{t('stats.saved')}</dt>
					<dd data-test-saved class="text-2xl font-semibold tabular-nums">
						{stats.totals.saved}
					</dd>
				</div>
				<div class="rounded-2xl border p-4">
					<dt class="text-xs text-muted-foreground">{t('stats.favorites')}</dt>
					<dd data-test-favorites class="text-2xl font-semibold tabular-nums">
						{stats.totals.favorites}
					</dd>
				</div>
			</dl>

			<section class="flex flex-col gap-3 rounded-2xl border p-4">
				<h2 class="text-base font-semibold">{t('stats.dailyTitle')}</h2>
				<DailyBars daily={stats.daily} />
			</section>

			<div class="grid gap-4 md:grid-cols-3">
				<RankedBars
					testId="feeds"
					title={t('stats.topFeeds')}
					items={stats.top_feeds.map((feed) => ({
						key: feed.id,
						label: feed.name,
						count: feed.articles_read
					}))}
				/>
				<RankedBars
					testId="authors"
					title={t('stats.topAuthors')}
					items={stats.top_authors.map((author) => ({
						key: author.id,
						label: author.name,
						count: author.articles_read
					}))}
				/>
				<RankedBars
					testId="keywords"
					title={t('stats.topKeywords')}
					items={stats.top_keywords.map((keyword) => ({
						key: keyword.term,
						label: keyword.term,
						count: keyword.articles_read
					}))}
				/>
			</div>

			<section class="flex flex-col gap-3 rounded-2xl border p-4">
				<div>
					<h2 class="text-base font-semibold">{t('stats.engagementTitle')}</h2>
					<p class="text-sm text-muted-foreground">{t('stats.engagementHint')}</p>
				</div>
				<FeedEngagementTable feeds={stats.feed_engagement} />
			</section>

			<section data-test-popularity class="flex flex-col gap-3 rounded-2xl border p-4">
				<div>
					<h2 class="text-base font-semibold">{t('stats.popularTitle')}</h2>
					<p class="text-sm text-muted-foreground">
						{t('stats.popularIntro', { min: popularity?.min_readers ?? 0 })}
					</p>
				</div>
				{#if !popularity || popularity.articles.length === 0}
					<p data-test-popularity-empty class="text-sm text-muted-foreground">
						{t('stats.popularEmpty')}
					</p>
				{:else}
					<ul class="flex flex-col gap-2">
						{#each popularity.articles as article (article.url)}
							<li
								data-test-popular-article
								class="flex items-baseline justify-between gap-3 text-sm"
							>
								<a href={article.url} rel="noopener noreferrer" class="truncate underline">
									{article.title}
								</a>
								<span class="shrink-0 tabular-nums text-muted-foreground">
									{t('stats.readers', { count: article.readers })}
								</span>
							</li>
						{/each}
					</ul>
				{/if}
			</section>
		</div>
	{/if}
</div>
