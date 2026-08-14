<script lang="ts">
	import { cn } from '../technical/utils.js';
	import GlareHover from '../technical/effects/glare-hover.svelte';
	import BorderGlow from '../technical/effects/border-glow.svelte';

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
		/** Estimated minutes to read, from the backend's word count. */
		readingMinutes?: number | null;
		/** Already-read articles are dimmed so the unread ones stand out at a glance. */
		read?: boolean;
		/** 0 to 1. Drawn as a thin bar at the bottom of the tile when reading started. */
		scrollProgress?: number;
		/** The feed's own icon, proxied by the API. Falls back to the source's initial. */
		iconUrl?: string | null;
		/** 0-100 affinity. Hidden at the neutral 50, where the number would say nothing. */
		relevanceScore?: number | null;
		// Text and date formatting come from the app: this package must not depend on its i18n, and a
		// design system that hardcodes one language can't be reused.
		locale?: string;
		readLabel?: string;
		scoreTitle?: string;
		scoreSuffix?: string;
		minutesLabel?: (minutes: number) => string;
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
		readingMinutes = null,
		read = false,
		scrollProgress = 0,
		iconUrl = null,
		relevanceScore = null,
		locale = 'en',
		readLabel = 'read',
		scoreTitle,
		scoreSuffix = 'out of 100 for relevance',
		minutesLabel = (minutes: number) => `${minutes} min`,
		class: className
	}: Props = $props();

	let imageFailed = $state(false);
	let iconFailed = $state(false);

	const formattedDate = $derived(
		new Date(publishedAt).toLocaleDateString(locale, { day: 'numeric', month: 'short' })
	);
	const initial = $derived(sourceLabel.charAt(0).toUpperCase());
	const progressPercent = $derived(Math.round(Math.min(Math.max(scrollProgress, 0), 1) * 100));
	const showsScore = $derived(relevanceScore !== null && relevanceScore !== 50);
</script>

<a
	{href}
	class={cn(
		'group relative flex animate-in flex-col overflow-hidden rounded-2xl border bg-card shadow-sm fade-in slide-in-from-bottom-4 transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-xl',
		featured ? 'sm:col-span-2 lg:col-span-2' : '',
		read ? 'opacity-60 hover:opacity-100' : '',
		className
	)}
>
	{#if featured}
		<BorderGlow />
	{/if}

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

		<GlareHover class="absolute inset-0" glareColor="#ffffff" glareOpacity={0.35} glareSize={200} />

		<div class="absolute right-2 top-2 flex items-center gap-1">
			{#if showsScore}
				<span
					class="rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-semibold text-white backdrop-blur"
					title={scoreTitle}
				>
					{relevanceScore}
					<span class="sr-only">{scoreSuffix}</span>
				</span>
			{/if}
			{#if readingMinutes}
				<span
					class="rounded-full bg-black/60 px-2 py-0.5 text-[11px] font-medium text-white backdrop-blur"
				>
					{minutesLabel(readingMinutes)}
				</span>
			{/if}
		</div>
	</div>

	<div class="flex flex-1 flex-col gap-1.5 p-4">
		<!-- The avatar lives here, not inside the image box: that box is overflow-hidden, which used
			 to clip the overlapping circle in half. A negative margin keeps the overlap look. -->
		<span
			class="-mt-8 mb-1 flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-full text-xs font-bold text-white shadow-md ring-4 ring-card"
			style={`background: hsl(${accentHue} 65% 45%);`}
		>
			{#if iconUrl && !iconFailed}
				<img
					src={iconUrl}
					alt=""
					class="size-full object-cover"
					loading="lazy"
					onerror={() => (iconFailed = true)}
				/>
			{:else}
				{initial}
			{/if}
		</span>
		<span class="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
			{sourceLabel}
			{#if read}
				<span class="normal-case tracking-normal">· {readLabel}</span>
			{/if}
		</span>
		<h3
			style={`view-transition-name: article-title-${id};`}
			class={cn(
				'font-serif leading-snug transition-transform duration-200 group-hover:-translate-y-0.5',
				featured ? 'line-clamp-3 text-xl sm:text-2xl' : 'line-clamp-2 text-base',
				read ? 'font-normal' : featured ? 'font-bold' : 'font-semibold'
			)}
		>
			{title}
		</h3>
		{#if featured && summary}
			<p class="line-clamp-2 text-sm text-muted-foreground">{summary}</p>
		{/if}
		<span class="mt-auto pt-1 text-xs text-muted-foreground">{formattedDate}</span>
	</div>

	{#if progressPercent > 0 && progressPercent < 100}
		<div aria-hidden="true" class="h-0.5 w-full bg-muted">
			<div class="h-full bg-primary" style={`width: ${progressPercent}%;`}></div>
		</div>
	{/if}
</a>
