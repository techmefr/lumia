<script lang="ts">
	import type { FeedEngagement } from '@lumia/core';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		feeds: FeedEngagement[];
	}

	let { feeds }: Props = $props();
</script>

{#if feeds.length === 0}
	<p data-test-engagement-empty class="text-sm text-muted-foreground">{t('stats.nothingYet')}</p>
{:else}
	<div class="overflow-x-auto">
		<table data-test-engagement class="w-full text-start text-sm">
			<caption class="sr-only">{t('stats.engagementTitle')}</caption>
			<thead class="text-xs text-muted-foreground">
				<tr>
					<th scope="col" class="py-2 pe-3 text-start font-medium">{t('stats.colFeed')}</th>
					<th scope="col" class="px-3 py-2 text-end font-medium">{t('stats.colReceived')}</th>
					<th scope="col" class="px-3 py-2 text-end font-medium">{t('stats.colRead')}</th>
					<th scope="col" class="px-3 py-2 text-end font-medium">{t('stats.colIgnored')}</th>
					<th scope="col" class="py-2 ps-3 text-start font-medium">{t('stats.colRatio')}</th>
				</tr>
			</thead>
			<tbody>
				{#each feeds as feed (feed.feed_id)}
					{@const percent = Math.round(feed.read_ratio * 100)}
					<tr data-test-engagement-row={feed.feed_id} class="border-t">
						<th scope="row" class="py-2 pe-3 text-start font-normal">{feed.title}</th>
						<td class="px-3 py-2 text-end tabular-nums">{feed.received}</td>
						<td class="px-3 py-2 text-end tabular-nums">{feed.read}</td>
						<td class="px-3 py-2 text-end tabular-nums">{feed.ignored}</td>
						<td class="py-2 ps-3">
							<div class="flex items-center gap-2">
								<div aria-hidden="true" class="h-1.5 w-20 rounded-full bg-muted">
									<div class="h-full rounded-full bg-primary" style="width: {percent}%"></div>
								</div>
								<span data-test-engagement-ratio class="tabular-nums text-muted-foreground">
									{t('stats.percentRead', { percent })}
								</span>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}
