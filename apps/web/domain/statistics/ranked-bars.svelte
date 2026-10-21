<script lang="ts">
	import { t } from '$technical/i18n/i18n.svelte';

	interface RankedItem {
		key: string;
		label: string;
		count: number;
	}

	interface Props {
		title: string;
		items: RankedItem[];
		testId: string;
	}

	let { title, items, testId }: Props = $props();

	const peak = $derived(Math.max(1, ...items.map((item) => item.count)));
</script>

<section data-test-ranked={testId} class="flex flex-col gap-3 rounded-2xl border p-4">
	<h3 class="text-sm font-semibold">{title}</h3>
	{#if items.length === 0}
		<p data-test-ranked-empty class="text-sm text-muted-foreground">{t('stats.nothingYet')}</p>
	{:else}
		<ol class="flex flex-col gap-2">
			{#each items as item (item.key)}
				<li data-test-ranked-item={item.key} class="flex flex-col gap-1">
					<div class="flex items-baseline justify-between gap-2 text-sm">
						<span class="truncate">{item.label}</span>
						<span class="shrink-0 tabular-nums text-muted-foreground">{item.count}</span>
					</div>
					<div aria-hidden="true" class="h-1.5 rounded-full bg-muted">
						<div
							class="h-full rounded-full bg-primary"
							style="width: {(item.count / peak) * 100}%"
						></div>
					</div>
				</li>
			{/each}
		</ol>
	{/if}
</section>
