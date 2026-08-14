<script lang="ts">
	import type { ArticleSummary } from '@lumia/core';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import Star from '@lucide/svelte/icons/star';
	import { accentHueForFeed } from './accent-hue.js';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articles: ArticleSummary[];
		onLike: (article: ArticleSummary) => void;
		onDislike: (article: ArticleSummary) => void;
		onSave: (article: ArticleSummary) => void;
		onFavorite: (article: ArticleSummary) => void;
		onOpen: (article: ArticleSummary) => void;
	}

	let { articles, onLike, onDislike, onSave, onFavorite, onOpen }: Props = $props();

	let currentIndex = $state(0);
	let dragX = $state(0);
	let dragY = $state(0);
	let dragging = $state(false);
	type SwipeAction = 'like' | 'dislike' | 'favorite' | 'save';

	let exiting = $state<SwipeAction | null>(null);
	let pointerStart = { x: 0, y: 0, time: 0 };

	const visible = $derived(articles.slice(currentIndex, currentIndex + 3));
	const current = $derived(articles[currentIndex]);

	const SWIPE_THRESHOLD = 110;
	/** How far the card flies off once a direction is committed. */
	const EXIT_DISTANCE = 600;

	function onPointerDown(event: PointerEvent) {
		if (exiting) return;
		dragging = true;
		pointerStart = { x: event.clientX, y: event.clientY, time: Date.now() };
		(event.target as HTMLElement).setPointerCapture(event.pointerId);
	}

	function onPointerMove(event: PointerEvent) {
		if (!dragging) return;
		dragX = event.clientX - pointerStart.x;
		dragY = event.clientY - pointerStart.y;
	}

	function onPointerUp() {
		if (!dragging) return;
		dragging = false;
		const elapsed = Date.now() - pointerStart.time;
		if (Math.abs(dragX) < 8 && Math.abs(dragY) < 8 && elapsed < 300) {
			if (current) onOpen(current);
			dragX = 0;
			dragY = 0;
			return;
		}
		// The dominant axis decides, so a diagonal drag resolves to one intent rather than firing
		// both. Horizontal wins a tie: left/right are the two gestures every card game teaches.
		const action =
			Math.abs(dragX) >= Math.abs(dragY)
				? Math.abs(dragX) > SWIPE_THRESHOLD
					? dragX > 0
						? 'like'
						: 'dislike'
					: null
				: Math.abs(dragY) > SWIPE_THRESHOLD
					? dragY < 0
						? 'favorite'
						: 'save'
					: null;
		if (action) {
			commit(action);
		} else {
			dragX = 0;
			dragY = 0;
		}
	}

	function commit(action: SwipeAction) {
		exiting = action;
		if (action === 'like') dragX = EXIT_DISTANCE;
		else if (action === 'dislike') dragX = -EXIT_DISTANCE;
		else if (action === 'favorite') dragY = -EXIT_DISTANCE;
		else dragY = EXIT_DISTANCE;

		const article = current;
		setTimeout(() => {
			if (article) {
				if (action === 'like') onLike(article);
				else if (action === 'dislike') onDislike(article);
				else if (action === 'favorite') onFavorite(article);
				else onSave(article);
			}
			// Favorite and save don't record a sentiment, so the backend may serve the article again
			// later; advancing here is about this session's stack, not about hiding it forever.
			currentIndex += 1;
			exiting = null;
			dragX = 0;
			dragY = 0;
		}, 250);
	}

	const rotation = $derived(dragX / 18);
	const likeOpacity = $derived(Math.min(Math.max(dragX / SWIPE_THRESHOLD, 0), 1));
	const dislikeOpacity = $derived(Math.min(Math.max(-dragX / SWIPE_THRESHOLD, 0), 1));
	const favoriteOpacity = $derived(Math.min(Math.max(-dragY / SWIPE_THRESHOLD, 0), 1));
	const saveOpacity = $derived(Math.min(Math.max(dragY / SWIPE_THRESHOLD, 0), 1));
</script>

{#if current}
	<div class="relative mx-auto flex w-full max-w-md flex-col items-center gap-6">
		<div class="relative h-[28rem] w-full">
			{#each visible as article, stackIndex (article.id)}
				{@const isTop = stackIndex === 0}
				<div
					class="absolute inset-0 flex flex-col overflow-hidden rounded-3xl border bg-card shadow-lg select-none"
					style={isTop
						? `transform: translate(${dragX}px, ${dragY}px) rotate(${rotation}deg); transition: ${dragging ? 'none' : 'transform 300ms ease-out'}; touch-action: none; cursor: grab; z-index: 3;`
						: `transform: scale(${1 - stackIndex * 0.05}) translateY(${stackIndex * 12}px); opacity: ${1 - stackIndex * 0.25}; z-index: ${3 - stackIndex};`}
					onpointerdown={isTop ? onPointerDown : undefined}
					onpointermove={isTop ? onPointerMove : undefined}
					onpointerup={isTop ? onPointerUp : undefined}
					onpointercancel={isTop ? onPointerUp : undefined}
					aria-hidden={isTop ? undefined : 'true'}
				>
					<div
						class="relative h-64 w-full shrink-0 overflow-hidden"
						style={`background: linear-gradient(135deg, hsl(${accentHueForFeed(article.feed_id)} 70% 55%), hsl(${accentHueForFeed(article.feed_id) + 40} 70% 45%));`}
					>
						{#if article.image_url}
							<img src={article.image_url} alt="" class="absolute inset-0 h-full w-full object-cover" />
						{/if}
						<div
							class="absolute inset-0 bg-gradient-to-t from-black/85 via-black/10 to-transparent"
						></div>
						<div class="absolute inset-x-0 bottom-0 flex flex-col gap-1 p-4 text-white">
							<span
								class="w-fit rounded-full bg-white/15 px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide backdrop-blur-sm"
							>
								{article.source_label}
							</span>
							<h2 class="line-clamp-2 font-serif text-xl font-bold leading-tight">{article.title}</h2>
						</div>
					</div>
					{#if article.summary}
						<p class="line-clamp-4 flex-1 p-4 text-sm text-muted-foreground">{article.summary}</p>
					{/if}

					{#if isTop}
						<div
							aria-hidden="true"
							class="pointer-events-none absolute left-6 top-6 rounded-lg border-4 border-emerald-500 px-3 py-1 text-lg font-bold uppercase text-emerald-500"
							style={`opacity: ${likeOpacity}; transform: rotate(-15deg);`}
						>
							{t('swipe.like')}
						</div>
						<div
							aria-hidden="true"
							class="pointer-events-none absolute right-6 top-6 rounded-lg border-4 border-rose-500 px-3 py-1 text-lg font-bold uppercase text-rose-500"
							style={`opacity: ${dislikeOpacity}; transform: rotate(15deg);`}
						>
							{t('swipe.no')}
						</div>
						<div
							aria-hidden="true"
							class="pointer-events-none absolute inset-x-0 top-6 mx-auto w-fit rounded-lg border-4 border-amber-500 px-3 py-1 text-lg font-bold uppercase text-amber-500"
							style={`opacity: ${favoriteOpacity};`}
						>
							{t('swipe.favorite')}
						</div>
						<div
							aria-hidden="true"
							class="pointer-events-none absolute inset-x-0 bottom-6 mx-auto w-fit rounded-lg border-4 border-primary px-3 py-1 text-lg font-bold uppercase text-primary"
							style={`opacity: ${saveOpacity};`}
						>
							{t('swipe.readLater')}
						</div>
					{/if}
				</div>
			{/each}
		</div>

		<p aria-live="polite" class="sr-only">
			{t('swipe.remaining', { title: current.title, count: articles.length - currentIndex })}
		</p>

		<button
			onclick={() => onOpen(current)}
			class="rounded-md px-3 py-2 text-sm font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
		>
			{t('article.open')}
		</button>

		<div class="flex items-center gap-4">
			<button
				onclick={() => commit('dislike')}
				aria-label={t('article.dislike')}
				class="flex size-14 items-center justify-center rounded-full border-2 border-rose-500 text-rose-500 shadow-sm transition-transform hover:scale-110 active:scale-95"
			>
				<ThumbsDown class="size-6" />
			</button>
			<button
				onclick={() => commit('save')}
				aria-label={t('article.save')}
				class="flex size-11 items-center justify-center rounded-full border-2 border-primary text-primary shadow-sm transition-transform hover:scale-110 active:scale-95"
			>
				<Bookmark class="size-5" />
			</button>
			<button
				onclick={() => commit('favorite')}
				aria-label={t('swipe.favoriteAction')}
				class="flex size-11 items-center justify-center rounded-full border-2 border-amber-500 text-amber-500 shadow-sm transition-transform hover:scale-110 active:scale-95"
			>
				<Star class="size-5" />
			</button>
			<button
				onclick={() => commit('like')}
				aria-label={t('article.like')}
				class="flex size-14 items-center justify-center rounded-full border-2 border-emerald-500 text-emerald-500 shadow-sm transition-transform hover:scale-110 active:scale-95"
			>
				<ThumbsUp class="size-6" />
			</button>
		</div>
	</div>
{/if}
