<script lang="ts">
	import { cn } from '../technical/utils.js';

	interface Props {
		href: string;
		title: string;
		summary?: string | null;
		sourceLabel: string;
		publishedAt: string;
		/** Deterministic 0-360 hue so each source gets a stable cover color, Flipboard-style. */
		accentHue: number;
		class?: string;
	}

	let { href, title, summary, sourceLabel, publishedAt, accentHue, class: className }: Props =
		$props();

	const formattedDate = $derived(
		new Date(publishedAt).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
	);
</script>

<a
	{href}
	class={cn(
		'group flex flex-col overflow-hidden rounded-xl border bg-card shadow-sm transition-shadow hover:shadow-md',
		className
	)}
>
	<div
		class="h-28 w-full"
		style={`background: linear-gradient(135deg, hsl(${accentHue} 70% 55%), hsl(${accentHue + 40} 70% 45%));`}
	></div>
	<div class="flex flex-1 flex-col gap-2 p-4">
		<span class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
			{sourceLabel}
		</span>
		<h3 class="line-clamp-2 font-serif text-lg font-semibold leading-snug group-hover:underline">
			{title}
		</h3>
		{#if summary}
			<p class="line-clamp-3 text-sm text-muted-foreground">{summary}</p>
		{/if}
		<span class="mt-auto pt-1 text-xs text-muted-foreground">{formattedDate}</span>
	</div>
</a>
