<script lang="ts">
	import { base } from '$app/paths';
	import type { ArticleSummary } from '@lumia/core';
	import { ArticleCard, ArticleCardSkeleton, ArticleHero, GradualBlur } from '@lumia/ui';
	import Inbox from '@lucide/svelte/icons/inbox';
	import { accentHueForFeed } from './accent-hue';
	import { feedIcons } from '$technical/api/feed-icons.svelte';
	import { getLocale, t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articles: ArticleSummary[];
		loading: boolean;
		/** Index of the keyboard-focused card, or -1 when navigation hasn't started. */
		cursor?: number;
		/** Kiosque layout: the first article becomes a full-width lead, the rest keep the grid. */
		hero?: boolean;
		/** Shown when there is nothing to display; put the next action in here, not a dead end. */
		empty?: import('svelte').Snippet;
		/** Rendered under the grid — typically the "load more" button. */
		footer?: import('svelte').Snippet;
	}

	let { articles, loading, cursor = -1, hero = false, empty, footer }: Props = $props();

	const SKELETON_COUNT = 6;

	const lead = $derived(hero ? articles[0] : undefined);
	const rest = $derived(lead ? articles.slice(1) : articles);
	/** The grid indices shift by one when a lead is pulled out; the cursor has to follow. */
	const gridCursor = $derived(lead ? cursor - 1 : cursor);

	// The cards live in the design system, which knows nothing of the app's i18n: their text and the
	// locale their dates are formatted in are handed over as props.
	const cardLabels = $derived({
		locale: getLocale(),
		readLabel: t('article.read'),
		scoreTitle: t('article.relevanceTitle'),
		scoreSuffix: t('article.scoreSuffix'),
		minutesLabel: (minutes: number) => t('common.minutes', { count: minutes })
	});
</script>

{#if loading && articles.length === 0}
	<div role="status" aria-label={t('grid.loading')} class="flex flex-col gap-4">
		{#if hero}
			<ArticleCardSkeleton featured />
		{/if}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each Array(SKELETON_COUNT), index}
				<ArticleCardSkeleton featured={!hero && index === 0} />
			{/each}
		</div>
	</div>
{:else if articles.length === 0}
	{#if empty}
		{@render empty()}
	{:else}
		<p class="flex items-center gap-2 text-sm text-muted-foreground">
			<Inbox class="size-4" />
			{t('grid.empty')}
		</p>
	{/if}
{:else}
	<div class="relative flex flex-col gap-4">
		{#if lead}
			<ArticleHero
				id={lead.id}
				href="{base}/articles/{lead.id}"
				title={lead.title}
				summary={lead.summary}
				imageUrl={lead.image_url}
				sourceLabel={lead.source_label}
				publishedAt={lead.published_at}
				accentHue={accentHueForFeed(lead.feed_id)}
				readingMinutes={lead.reading_minutes}
				read={lead.read}
				iconUrl={feedIcons.get(lead.feed_id)}
				relevanceScore={lead.relevance_score}
				{...cardLabels}
				ctaLabel={t('article.heroCta')}
				class={cursor === 0 ? 'ring-2 ring-ring ring-offset-2 ring-offset-background' : ''}
			/>
		{/if}
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each rest as article, index (article.id)}
				<ArticleCard
					id={article.id}
					href="{base}/articles/{article.id}"
					title={article.title}
					summary={article.summary}
					imageUrl={article.image_url}
					sourceLabel={article.source_label}
					publishedAt={article.published_at}
					accentHue={accentHueForFeed(article.feed_id)}
					featured={!lead && index === 0}
					readingMinutes={article.reading_minutes}
					read={article.read}
					scrollProgress={article.scroll_progress}
					iconUrl={feedIcons.get(article.feed_id)}
					relevanceScore={article.relevance_score}
					{...cardLabels}
					class={index === gridCursor ? 'ring-2 ring-ring ring-offset-2 ring-offset-background' : ''}
				/>
			{/each}
		</div>
		<GradualBlur position="bottom" height="3rem" strength={1.5} target="parent" />
	</div>
	{#if footer}
		{@render footer()}
	{/if}
{/if}
