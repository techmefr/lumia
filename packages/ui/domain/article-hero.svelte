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
		accentHue: number;
		readingMinutes?: number | null;
		read?: boolean;
		iconUrl?: string | null;
		relevanceScore?: number | null;
		// Text and date formatting come from the app: this package must not depend on its i18n, and a
		// design system that hardcodes one language can't be reused.
		locale?: string;
		readLabel?: string;
		scoreTitle?: string;
		scoreSuffix?: string;
		minutesLabel?: (minutes: number) => string;
		ctaLabel?: string;
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
		readingMinutes = null,
		read = false,
		iconUrl = null,
		relevanceScore = null,
		locale = 'en',
		readLabel = 'read',
		scoreTitle,
		scoreSuffix = 'out of 100 for relevance',
		minutesLabel = (minutes: number) => `${minutes} min`,
		ctaLabel = 'Read the lead →',
		class: className
	}: Props = $props();

	let imageFailed = $state(false);
	let iconFailed = $state(false);

	const formattedDate = $derived(
		new Date(publishedAt).toLocaleDateString(locale, {
			day: 'numeric',
			month: 'long'
		})
	);
	const initial = $derived(sourceLabel.charAt(0).toUpperCase());
	const showsScore = $derived(relevanceScore !== null && relevanceScore !== 50);
</script>

<a
	{href}
	class={cn(
		'group relative grid animate-in overflow-hidden rounded-2xl border bg-card shadow-sm fade-in slide-in-from-bottom-4 transition-all duration-300 ease-out hover:shadow-xl md:grid-cols-2',
		read ? 'opacity-70 hover:opacity-100' : '',
		className
	)}
>
	<BorderGlow />

	<div
		class="relative h-56 w-full overflow-hidden md:h-full md:min-h-[22rem]"
		style={`background: linear-gradient(135deg, hsl(${accentHue} 45% 55% / 20%), hsl(${accentHue + 40} 45% 45% / 28%)), var(--card, #fff); view-transition-name: article-image-${id};`}
	>
		{#if imageUrl && !imageFailed}
			<img
				src={imageUrl}
				alt=""
				class="absolute inset-0 h-full w-full object-cover transition-transform duration-700 ease-out group-hover:scale-105"
				onerror={() => (imageFailed = true)}
			/>
		{:else}
			<div
				class="absolute inset-0"
				style={`background-image: radial-gradient(circle at 30% 25%, hsl(${accentHue + 60} 50% 70% / 20%), transparent 70%);`}
			></div>
		{/if}
		<GlareHover class="absolute inset-0" glareColor="#ffffff" glareOpacity={0.3} glareSize={280} />
	</div>

	<div class="flex flex-col gap-3 p-6 sm:p-8">
		<div class="flex items-center gap-2">
			<span
				class="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-full text-xs font-bold text-white shadow-md"
				style={`background: hsl(${accentHue} 65% 45%);`}
			>
				{#if iconUrl && !iconFailed}
					<img
						src={iconUrl}
						alt=""
						class="size-full object-cover"
						onerror={() => (iconFailed = true)}
					/>
				{:else}
					{initial}
				{/if}
			</span>
			<span class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
				{sourceLabel}
			</span>
			<span class="text-xs text-muted-foreground">· {formattedDate}</span>
			{#if read}
				<span class="text-xs text-muted-foreground">· {readLabel}</span>
			{/if}
		</div>

		<h2 class="font-serif text-2xl font-bold leading-tight sm:text-3xl lg:text-4xl">
			{title}
		</h2>

		{#if summary}
			<p class="line-clamp-4 text-sm text-muted-foreground sm:text-base">{summary}</p>
		{/if}

		<div class="mt-auto flex flex-wrap items-center gap-2 pt-2 text-xs text-muted-foreground">
			{#if readingMinutes}
				<span class="rounded-full bg-secondary px-2 py-0.5 font-medium text-secondary-foreground">
					{minutesLabel(readingMinutes)}
				</span>
			{/if}
			{#if showsScore}
				<span
					class="rounded-full bg-primary/10 px-2 py-0.5 font-semibold text-primary"
					title={scoreTitle}
				>
					{relevanceScore}<span class="sr-only">{scoreSuffix}</span>
				</span>
			{/if}
			<span class="ml-auto font-medium text-primary group-hover:underline">{ctaLabel}</span>
		</div>
	</div>
</a>
