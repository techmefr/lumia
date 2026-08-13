<script lang="ts">
	import { cn } from '../technical/utils.js';

	interface Props {
		id: string;
		href: string;
		title: string;
		summary?: string | null;
		imageUrl?: string | null;
		sourceLabel: string;
		publishedAt: string;
		/** Deterministic 0-360 hue so each source gets a stable avatar color, bento-style. */
		accentHue: number;
		/** Larger tile for the lead story in a bento grid. */
		featured?: boolean;
		class?: string;
	}

	let {
		id,
		href,
		title,
		summary,
		imageUrl,
		sourceLabel,
		publishedAt,
		accentHue,
		featured = false,
		class: className
	}: Props = $props();

	let imageFailed = $state(false);

	const formattedDate = $derived(
		new Date(publishedAt).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
	);
	const initial = $derived(sourceLabel.charAt(0).toUpperCase());
</script>

<a
	{href}
	class={cn(
		'group flex animate-in flex-col overflow-hidden rounded-2xl border bg-card shadow-sm fade-in slide-in-from-bottom-4 transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-xl',
		featured ? 'sm:col-span-2 lg:col-span-2' : '',
		className
	)}
>
	<div
		class={cn('relative w-full overflow-hidden', featured ? 'h-64 sm:h-80' : 'h-36')}
		style={`background: linear-gradient(135deg, hsl(${accentHue} 70% 55%), hsl(${accentHue + 40} 70% 45%)); view-transition-name: article-image-${id};`}
	>
		{#if imageUrl && !imageFailed}
			<img
				src={imageUrl}
				alt=""
				loading="lazy"
				class="absolute inset-0 h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-110"
				onerror={() => (imageFailed = true)}
			/>
		{:else}
			<div
				class="absolute inset-0 opacity-90 transition-transform duration-500 ease-out group-hover:scale-110"
				style={`background-image: radial-gradient(circle at 30% 30%, hsl(${accentHue + 60} 80% 75% / 60%), transparent 65%);`}
			></div>
		{/if}

		<span
			class="absolute -bottom-3 left-3 flex size-9 items-center justify-center rounded-full text-xs font-bold text-white shadow-md ring-4 ring-card"
			style={`background: hsl(${accentHue} 65% 45%);`}
		>
			{initial}
		</span>
	</div>

	<div class="flex flex-1 flex-col gap-1.5 p-4 pt-5">
		<span class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
			{sourceLabel}
		</span>
		<h3
			class={cn(
				'font-serif leading-snug transition-transform duration-200 group-hover:-translate-y-0.5',
				featured ? 'line-clamp-3 text-xl font-bold sm:text-2xl' : 'line-clamp-2 text-base font-semibold'
			)}
		>
			{title}
		</h3>
		{#if featured && summary}
			<p class="line-clamp-2 text-sm text-muted-foreground">{summary}</p>
		{/if}
		<span class="mt-auto pt-1 text-xs text-muted-foreground">{formattedDate}</span>
	</div>
</a>
