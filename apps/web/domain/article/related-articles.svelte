<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { ArticleCard } from '@lumia/ui';
	import { lumia } from '$technical/api/client';
	import { feedIcons } from '$technical/api/feed-icons.svelte';
	import { getLocale, t } from '$technical/i18n/i18n.svelte';
	import { accentHueForFeed } from './accent-hue';

	let { articleId }: { articleId: string } = $props();

	let related = $state<ArticleSummary[]>([]);

	const cardLabels = $derived({
		locale: getLocale(),
		readLabel: t('article.read'),
		scoreTitle: t('article.relevanceTitle'),
		scoreSuffix: t('article.scoreSuffix'),
		minutesLabel: (minutes: number) => t('common.minutes', { count: minutes })
	});

	// A failed lookup leaves the section out: it is a suggestion, not something the page needs.
	onMount(() => {
		lumia.article
			.getRelatedArticles(articleId)
			.then((found) => (related = found))
			.catch(() => {});
	});
</script>

{#if related.length > 0}
	<section data-test-related aria-labelledby="related-heading" class="mt-4 print:hidden">
		<h2 id="related-heading" class="mb-3 text-lg font-semibold">{t('article.related')}</h2>
		<ul class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each related as item (item.id)}
				<li data-test-related-item={item.id}>
					<ArticleCard
						id={item.id}
						href="{base}/articles/{item.id}"
						title={item.title}
						summary={item.summary}
						imageUrl={item.image_url}
						sourceLabel={item.source_label}
						publishedAt={item.published_at}
						accentHue={accentHueForFeed(item.feed_id)}
						readingMinutes={item.reading_minutes}
						read={item.read}
						scrollProgress={item.scroll_progress}
						iconUrl={feedIcons.get(item.feed_id)}
						relevanceScore={item.relevance_score}
						{...cardLabels}
					/>
				</li>
			{/each}
		</ul>
	</section>
{/if}
