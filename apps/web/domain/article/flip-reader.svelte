<script lang="ts">
	import { base } from '$app/paths';
	import type { ArticleSummary } from '@lumia/core';
	import { Button } from '@lumia/ui';
	import X from '@lucide/svelte/icons/x';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';
	import Clock from '@lucide/svelte/icons/clock';
	import Gauge from '@lucide/svelte/icons/gauge';
	import { accentHueForFeed } from './accent-hue';
	import { getLocale, t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articles: ArticleSummary[];
		/** Page to open on; the caller passes its keyboard cursor so both stay in step. */
		startIndex?: number;
		onClose: () => void;
		/** Called with the page the reader stopped on, so the list can put its cursor there. */
		onPage?: (index: number) => void;
	}

	let { articles, startIndex = 0, onClose, onPage }: Props = $props();

	/** Below this, a horizontal drag is a hesitation rather than a page turn. */
	const SWIPE_THRESHOLD_PX = 60;

	// The starting page is deliberately a snapshot: the modal owns its cursor once open, and the list
	// gets it back through onPage.
	// svelte-ignore state_referenced_locally
	let index = $state(startIndex);
	let dragX = $state(0);
	let dragging = $state(false);
	let startX = 0;

	/** Clamped here rather than at init, so a shorter list can't leave the cursor past the end. */
	const page = $derived(Math.min(Math.max(index, 0), Math.max(articles.length - 1, 0)));
	const current = $derived(articles[page]);
	const hue = $derived(current ? accentHueForFeed(current.feed_id) : 0);
	const formattedDate = $derived(
		current
			? new Date(current.published_at).toLocaleDateString(getLocale(), {
					day: 'numeric',
					month: 'long'
				})
			: ''
	);

	function go(delta: number) {
		const next = page + delta;
		if (next < 0 || next >= articles.length) return;
		index = next;
		dragX = 0;
		onPage?.(next);
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			onClose();
			return;
		}
		if (event.key === 'ArrowRight' || event.key === 'j') go(1);
		if (event.key === 'ArrowLeft' || event.key === 'k') go(-1);
	}

	function onPointerDown(event: PointerEvent) {
		// Ignore secondary buttons and anything starting on the actions row.
		if (event.button !== 0) return;
		dragging = true;
		startX = event.clientX;
	}

	function onPointerMove(event: PointerEvent) {
		if (!dragging) return;
		dragX = event.clientX - startX;
	}

	function onPointerUp() {
		if (!dragging) return;
		dragging = false;
		if (dragX <= -SWIPE_THRESHOLD_PX) go(1);
		else if (dragX >= SWIPE_THRESHOLD_PX) go(-1);
		else dragX = 0;
	}
</script>

<svelte:window onkeydown={onKeydown} />

<!-- A modal surface rather than a route: feuilleter is a way of looking at the list you already
	 loaded, so closing it must put you back exactly where you were, filters and scroll included. -->
<div
	class="fixed inset-0 z-50 flex flex-col bg-background/98 backdrop-blur"
	role="dialog"
	aria-modal="true"
	aria-label={t('flip.dialog')}
>
	<div class="flex items-center justify-between gap-2 border-b px-4 py-3">
		<span data-test-flip-counter class="text-sm text-muted-foreground">
			{articles.length > 0 ? page + 1 : 0} / {articles.length}
		</span>
		<span class="hidden text-xs text-muted-foreground sm:block">
			{t('flip.hint')}
		</span>
		<Button data-test-flip-close variant="ghost" size="sm" onclick={onClose}>
			<X class="size-4" />
			{t('common.close')}
		</Button>
	</div>

	{#if current}
		<div
			data-test-flip-stage
			class="flex flex-1 items-center justify-center overflow-hidden px-4 py-6"
			role="group"
			aria-label={t('flip.page')}
			onpointerdown={onPointerDown}
			onpointermove={onPointerMove}
			onpointerup={onPointerUp}
			onpointercancel={onPointerUp}
		>
			<article
				class="flex max-h-full w-full max-w-2xl flex-col overflow-y-auto rounded-2xl border bg-card shadow-xl"
				style={`transform: translateX(${dragX}px) rotate(${dragX / 60}deg); transition: ${dragging ? 'none' : 'transform 220ms cubic-bezier(0.2, 0, 0, 1)'};`}
			>
				<div
					class="h-44 w-full shrink-0 overflow-hidden sm:h-56"
					style={`background: linear-gradient(135deg, hsl(${hue} 70% 55%), hsl(${hue + 40} 70% 45%));`}
				>
					{#if current.image_url}
						<img src={current.image_url} alt="" class="h-full w-full object-cover" />
					{/if}
				</div>
				<div class="flex flex-col gap-3 p-6">
					<span class="text-xs font-medium uppercase tracking-wide text-muted-foreground">
						{current.source_label} · {formattedDate}
					</span>
					<h2 class="font-serif text-2xl font-bold leading-tight sm:text-3xl">{current.title}</h2>
					{#if current.summary}
						<p class="text-sm text-muted-foreground sm:text-base">{current.summary}</p>
					{/if}
					<div class="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
						<span class="flex items-center gap-1">
							<Clock class="size-3.5" />
							{t('common.minutes', { count: current.reading_minutes ?? 0 })}
						</span>
						{#if current.relevance_score !== 50}
							<span class="flex items-center gap-1">
								<Gauge class="size-3.5" />
								{current.relevance_score}/100
							</span>
						{/if}
					</div>
					<Button data-test-flip-open class="mt-2 w-fit" href="{base}/articles/{current.id}"
						>{t('article.open')}</Button
					>
				</div>
			</article>
		</div>

		<div class="flex items-center justify-between gap-2 border-t px-4 py-3">
			<Button
				data-test-flip-prev
				variant="outline"
				size="sm"
				onclick={() => go(-1)}
				disabled={page === 0}
			>
				<ChevronLeft class="size-4" />
				{t('common.previous')}
			</Button>
			<Button
				data-test-flip-next
				variant="outline"
				size="sm"
				onclick={() => go(1)}
				disabled={page >= articles.length - 1}
			>
				{t('common.next')}
				<ChevronRight class="size-4" />
			</Button>
		</div>
	{:else}
		<p data-test-flip-empty class="flex flex-1 items-center justify-center text-sm text-muted-foreground">
			{t('flip.empty')}
		</p>
	{/if}
</div>
