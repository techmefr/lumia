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
		/** Selection mode: a checkbox appears on every card. Off, the list stays free of chrome. */
		selectable?: boolean;
		selectedIds?: string[];
		/** Index into `articles`. `extend` carries a shift-click, which takes the whole range. */
		onToggleSelect?: (index: number, options: { extend: boolean }) => void;
		/** Shown when there is nothing to display; put the next action in here, not a dead end. */
		empty?: import('svelte').Snippet;
		/** Rendered under the grid — typically the "load more" button. */
		footer?: import('svelte').Snippet;
	}

	let {
		articles,
		loading,
		cursor = -1,
		hero = false,
		selectable = false,
		selectedIds = [],
		onToggleSelect,
		empty,
		footer
	}: Props = $props();

	// Written once for the grid and its placeholders so a wide screen cannot show one column count
	// while loading and another once loaded. Past `lg` the room goes into columns rather than into
	// cards that keep growing: a card wider than its own image is mostly empty space.
	const GRID_COLUMNS =
		'grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 wide:grid-cols-6';

	const SKELETON_COUNT = 6;

	const lead = $derived(hero ? articles[0] : undefined);
	const rest = $derived(lead ? articles.slice(1) : articles);
	/** The grid indices shift by one when a lead is pulled out; the cursor has to follow. */
	const gridCursor = $derived(lead ? cursor - 1 : cursor);

	// The cards live in the design system, which knows nothing of the app's i18n: their text and the
	// locale their dates are formatted in are handed over as props.
	// The native default would toggle on its own and then be told a different answer by the state,
	// which shows as a flicker on a shift-click that extends a range rather than inverting it.
	function toggle(index: number, event: MouseEvent) {
		event.preventDefault();
		onToggleSelect?.(index, { extend: event.shiftKey });
	}

	const cardLabels = $derived({
		locale: getLocale(),
		readLabel: t('article.read'),
		scoreTitle: t('article.relevanceTitle'),
		scoreSuffix: t('article.scoreSuffix'),
		minutesLabel: (minutes: number) => t('common.minutes', { count: minutes })
	});
</script>

{#if loading && articles.length === 0}
	<div
		data-test-grid-loading
		role="status"
		aria-label={t('grid.loading')}
		class="flex flex-col gap-4"
	>
		{#if hero}
			<ArticleCardSkeleton featured />
		{/if}
		<div data-test-article-columns class={GRID_COLUMNS}>
			{#each Array(SKELETON_COUNT), index}
				<ArticleCardSkeleton featured={!hero && index === 0} />
			{/each}
		</div>
	</div>
{:else if articles.length === 0}
	{#if empty}
		{@render empty()}
	{:else}
		<p data-test-grid-empty class="flex items-center gap-2 text-sm text-muted-foreground">
			<Inbox class="size-4" />
			{t('grid.empty')}
		</p>
	{/if}
{:else}
	<div data-test-article-grid class="relative flex flex-col gap-4">
		{#if lead}
			{#if selectable}
				<div class="relative">
					{@render selectBox(lead, 0)}
					{@render heroCard(lead)}
				</div>
			{:else}
				{@render heroCard(lead)}
			{/if}
		{/if}
		<div data-test-article-columns class={GRID_COLUMNS}>
			{#each rest as article, index (article.id)}
				{#if selectable}
					<div class="relative">
						{@render selectBox(article, lead ? index + 1 : index)}
						{@render card(article, index)}
					</div>
				{:else}
					{@render card(article, index)}
				{/if}
			{/each}
		</div>
		<GradualBlur position="bottom" height="3rem" strength={1.5} target="parent" />
	</div>
	{#if footer}
		{@render footer()}
	{/if}
{/if}

{#snippet heroCard(article: ArticleSummary)}
	<ArticleHero
		id={article.id}
		href="{base}/articles/{article.id}"
		title={article.title}
		summary={article.summary}
		imageUrl={article.image_url}
		sourceLabel={article.source_label}
		publishedAt={article.published_at}
		accentHue={accentHueForFeed(article.feed_id)}
		readingMinutes={article.reading_minutes}
		read={article.read}
		iconUrl={feedIcons.get(article.feed_id)}
		relevanceScore={article.relevance_score}
		{...cardLabels}
		ctaLabel={t('article.heroCta')}
		class={cursor === 0 ? 'ring-2 ring-ring ring-offset-2 ring-offset-background' : ''}
	/>
{/snippet}

{#snippet card(article: ArticleSummary, index: number)}
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
{/snippet}

<!-- Rendered before the card so the keyboard reaches the checkbox first: a reader tabbing through
	 a selection is choosing articles, not opening them. It sits over the card rather than inside it: the cards belong to the design system,
	 which has no notion of a selection, and a list at rest keeps no trace of the feature. -->
{#snippet selectBox(article: ArticleSummary, position: number)}
	<input
		type="checkbox"
		data-test-select-article={article.id}
		class="absolute left-3 top-3 z-10 size-5 cursor-pointer accent-primary"
		checked={selectedIds.includes(article.id)}
		aria-label={t('selection.selectArticle', { title: article.title })}
		onclick={(event) => toggle(position, event)}
	/>
{/snippet}
