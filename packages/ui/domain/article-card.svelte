<script lang="ts">
	import ArrowRight from '@lucide/svelte/icons/arrow-right';
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
		'group flex animate-in flex-col overflow-hidden rounded-xl border bg-card shadow-sm fade-in slide-in-from-bottom-2 transition-all duration-300 hover:-translate-y-1 hover:shadow-lg',
		className
	)}
>
	<div
		class="h-28 w-full overflow-hidden"
		style={`background: linear-gradient(135deg, hsl(${accentHue} 70% 55%), hsl(${accentHue + 40} 70% 45%));`}
	>
		<div
			class="h-full w-full scale-100 opacity-90 transition-transform duration-500 group-hover:scale-110"
			style={`background-image: radial-gradient(circle at 30% 30%, hsl(${accentHue + 60} 80% 75% / 50%), transparent 60%);`}
		></div>
	</div>
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
		<span class="mt-auto flex items-center justify-between pt-1 text-xs text-muted-foreground">
			{formattedDate}
			<ArrowRight class="size-3.5 -translate-x-1 opacity-0 transition-all duration-200 group-hover:translate-x-0 group-hover:opacity-100" />
		</span>
	</div>
</a>
