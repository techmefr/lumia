<script lang="ts">
	import type { DailyReading } from '@lumia/core';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		daily: DailyReading[];
	}

	let { daily }: Props = $props();

	const busiest = $derived(
		daily.reduce<DailyReading | null>(
			(top, entry) => (entry.articles_read > (top?.articles_read ?? 0) ? entry : top),
			null
		)
	);
	const peak = $derived(busiest?.articles_read ?? 0);
	const total = $derived(daily.reduce((sum, entry) => sum + entry.articles_read, 0));
	const summary = $derived(
		busiest
			? t('stats.dailySummary', {
					articles: total,
					days: daily.length,
					day: busiest.day,
					max: peak
				})
			: t('stats.dailyNone')
	);
</script>

<figure class="flex flex-col gap-2">
	<!-- The bars carry no text of their own: the label on the chart and the table behind it are the
		 alternative, so a screen reader gets the figures instead of a row of anonymous shapes. -->
	<div data-test-daily-chart role="img" aria-label={summary} class="flex h-32 items-end gap-px">
		{#each daily as entry (entry.day)}
			<div
				data-test-daily-bar={entry.day}
				aria-hidden="true"
				class="min-h-px flex-1 rounded-t-sm {entry.articles_read > 0 ? 'bg-primary' : 'bg-muted'}"
				style="height: {peak > 0 ? Math.max((entry.articles_read / peak) * 100, 2) : 2}%"
			></div>
		{/each}
	</div>

	<table data-test-daily-table class="sr-only">
		<caption>{t('stats.dailyTitle')}</caption>
		<thead>
			<tr>
				<th scope="col">{t('stats.colDay')}</th>
				<th scope="col">{t('stats.colArticles')}</th>
				<th scope="col">{t('stats.colMinutes')}</th>
			</tr>
		</thead>
		<tbody>
			{#each daily as entry (entry.day)}
				<tr>
					<th scope="row">{entry.day}</th>
					<td>{entry.articles_read}</td>
					<td>{entry.reading_minutes}</td>
				</tr>
			{/each}
		</tbody>
	</table>

	<figcaption data-test-daily-summary class="text-xs text-muted-foreground">{summary}</figcaption>
</figure>
