<script lang="ts">
	import { cn } from '../technical/utils.js';

	interface Props {
		href: string;
		title: string;
		summary?: string | null;
		imageUrl?: string | null;
		sourceLabel: string;
		publishedAt: string;
		/** Deterministic 0-360 hue so each source gets a stable cover color, Flipboard-style. */
		accentHue: number;
		/** Large magazine-cover treatment for the lead story in a grid. */
		featured?: boolean;
		class?: string;
	}

	let {
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
</script>

<a
	{href}
	class={cn(
		'group relative flex animate-in overflow-hidden rounded-2xl shadow-md fade-in slide-in-from-bottom-4 transition-all duration-500 ease-out hover:shadow-2xl',
		featured ? 'sm:col-span-2 lg:col-span-2' : '',
		className
	)}
>
	<div
		class={cn(
			'relative w-full overflow-hidden',
			featured ? 'h-72 sm:h-96' : 'h-52'
		)}
		style={`background: linear-gradient(135deg, hsl(${accentHue} 70% 55%), hsl(${accentHue + 40} 70% 45%));`}
	>
		{#if imageUrl && !imageFailed}
			<img
				src={imageUrl}
				alt=""
				loading="lazy"
				class="absolute inset-0 h-full w-full scale-105 object-cover transition-transform duration-700 ease-out group-hover:scale-125"
				onerror={() => (imageFailed = true)}
			/>
		{:else}
			<div
				class="absolute inset-0 scale-105 opacity-90 transition-transform duration-700 ease-out group-hover:scale-125"
				style={`background-image: radial-gradient(circle at 30% 30%, hsl(${accentHue + 60} 80% 75% / 60%), transparent 65%);`}
			></div>
		{/if}

		<div
			class="absolute inset-0 bg-gradient-to-t from-black/90 via-black/25 to-transparent transition-opacity duration-300 group-hover:from-black/95"
		></div>

		<div class="absolute inset-x-0 bottom-0 flex flex-col gap-1.5 p-4 text-white sm:p-5">
			<span
				class="w-fit rounded-full bg-white/15 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide backdrop-blur-sm"
			>
				{sourceLabel}
			</span>
			<h3
				class={cn(
					'font-serif leading-tight drop-shadow-sm transition-transform duration-300 group-hover:-translate-y-0.5',
					featured ? 'line-clamp-3 text-2xl font-bold sm:text-3xl' : 'line-clamp-2 text-base font-semibold'
				)}
			>
				{title}
			</h3>
			{#if featured && summary}
				<p class="line-clamp-2 max-w-2xl text-sm text-white/85">{summary}</p>
			{/if}
			<span class="pt-0.5 text-xs text-white/70">{formattedDate}</span>
		</div>
	</div>
</a>
