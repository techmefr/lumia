<script lang="ts">
	import { base } from '$app/paths';
	import type { ArticleSummary } from '@lumia/core';
	import { ArticleCard, ArticleCardSkeleton, GradualBlur } from '@lumia/ui';
	import Inbox from '@lucide/svelte/icons/inbox';
	import { accentHueForFeed } from './accent-hue';
	import { feedIcons } from '$technical/api/feed-icons.svelte';

	interface Props {
		articles: ArticleSummary[];
		loading: boolean;
		/** Index of the keyboard-focused card, or -1 when navigation hasn't started. */
		cursor?: number;
		/** Shown when there is nothing to display; put the next action in here, not a dead end. */
		empty?: import('svelte').Snippet;
		/** Rendered under the grid — typically the "load more" button. */
		footer?: import('svelte').Snippet;
	}

	let { articles, loading, cursor = -1, empty, footer }: Props = $props();

	const SKELETON_COUNT = 6;
</script>

{#if loading && articles.length === 0}
	<div role="status" aria-label="Chargement des articles" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each Array(SKELETON_COUNT), index}
			<ArticleCardSkeleton featured={index === 0} />
		{/each}
	</div>
{:else if articles.length === 0}
	{#if empty}
		{@render empty()}
	{:else}
		<p class="flex items-center gap-2 text-sm text-muted-foreground">
			<Inbox class="size-4" />
			Aucun article.
		</p>
	{/if}
{:else}
	<div class="relative">
		<div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each articles as article, index (article.id)}
				<ArticleCard
					id={article.id}
					href="{base}/articles/{article.id}"
					title={article.title}
					summary={article.summary}
					imageUrl={article.image_url}
					sourceLabel={article.source_label}
					publishedAt={article.published_at}
					accentHue={accentHueForFeed(article.feed_id)}
					featured={index === 0}
					readingMinutes={article.reading_minutes}
					read={article.read}
					scrollProgress={article.scroll_progress}
					iconUrl={feedIcons.get(article.feed_id)}
					class={index === cursor ? 'ring-2 ring-ring ring-offset-2 ring-offset-background' : ''}
				/>
			{/each}
		</div>
		<GradualBlur position="bottom" height="3rem" strength={1.5} target="parent" />
	</div>
	{#if footer}
		{@render footer()}
	{/if}
{/if}
