<script lang="ts">
	import { base } from '$app/paths';
	import { onMount, tick } from 'svelte';
	import { page } from '$app/state';
	import { sanitizeArticleHtml, type ArticleDetail } from '@lumia/core';
	import { Button, Card, CardContent, Badge, GlareHover, ReadingProgress, Skeleton, toast } from '@lumia/ui';
	import ThumbsUp from '@lucide/svelte/icons/thumbs-up';
	import ThumbsDown from '@lucide/svelte/icons/thumbs-down';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import Star from '@lucide/svelte/icons/star';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import Tag from '@lucide/svelte/icons/tag';
	import Share2 from '@lucide/svelte/icons/share-2';
	import Check from '@lucide/svelte/icons/check';
	import Clock from '@lucide/svelte/icons/clock';
	import Volume2 from '@lucide/svelte/icons/volume-2';
	import Square from '@lucide/svelte/icons/square';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { SpeechReader } from '$technical/speech/speech.svelte';
	import AddToPlaylist from '$domain/playlist/add-to-playlist.svelte';

	/** Below this, "reading" is really just landing on the page; don't record it as progress. */
	const MIN_TRACKED_PROGRESS = 0.02;
	/** Past this, the article counts as read without the user having to say so. */
	const AUTO_READ_PROGRESS = 0.9;
	const SAVE_THROTTLE_MS = 1500;

	let article = $state<ArticleDetail | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let sentiment = $state<'like' | 'dislike' | null>(null);
	let saved = $state(false);
	let favorite = $state(false);
	let linkCopied = $state(false);
	let progress = $state(0);
	let contentEl = $state<HTMLElement | null>(null);

	const speech = new SpeechReader();

	let lastSaved = 0;
	let saveTimer: ReturnType<typeof setTimeout> | null = null;
	let markedRead = false;

	async function toggleSentiment(choice: 'like' | 'dislike') {
		if (!article) return;
		sentiment = sentiment === choice ? null : choice;
		await lumia.recommendation.sendFeedback(article.id, { sentiment });
		toast(sentiment === null ? 'Avis retiré.' : sentiment === 'like' ? 'Noté : j’aime.' : 'Noté : je n’aime pas.');
	}

	async function toggleSaved() {
		if (!article) return;
		saved = !saved;
		await lumia.recommendation.sendFeedback(article.id, { saved });
		toast(saved ? 'Ajouté à « À lire ».' : 'Retiré de « À lire ».');
	}

	async function toggleFavorite() {
		if (!article) return;
		favorite = !favorite;
		await lumia.recommendation.sendFeedback(article.id, { favorite });
		toast(favorite ? 'Ajouté aux favoris.' : 'Retiré des favoris.');
	}

	async function share() {
		if (!article) return;
		if (navigator.share) {
			try {
				await navigator.share({ title: article.title, url: article.url });
				return;
			} catch {
				return;
			}
		}
		await navigator.clipboard.writeText(article.url);
		linkCopied = true;
		setTimeout(() => (linkCopied = false), 2000);
	}

	function toggleSpeech() {
		if (!article) return;
		if (speech.speaking && !speech.paused) {
			speech.pause();
			return;
		}
		if (speech.paused) {
			speech.resume();
			return;
		}
		const text = `${article.title}. ${contentEl?.textContent ?? ''}`;
		speech.speak(text, { onDone: () => toast('Lecture terminée.') });
	}

	/** Fraction of the document scrolled past, clamped to [0, 1]. */
	function computeProgress(): number {
		const scrollable = document.documentElement.scrollHeight - window.innerHeight;
		if (scrollable <= 0) return 1;
		return Math.min(Math.max(window.scrollY / scrollable, 0), 1);
	}

	function persistProgress(value: number) {
		if (!article) return;
		void lumia.recommendation.sendFeedback(article.id, { scroll_progress: value });
	}

	function onScroll() {
		progress = computeProgress();
		if (progress < MIN_TRACKED_PROGRESS) return;

		if (!markedRead && progress >= AUTO_READ_PROGRESS && article) {
			markedRead = true;
			void lumia.recommendation.sendFeedback(article.id, { read: true });
		}

		// Throttle: a scroll fires dozens of times a second and each save is a request.
		const now = Date.now();
		if (now - lastSaved >= SAVE_THROTTLE_MS) {
			lastSaved = now;
			persistProgress(progress);
			return;
		}
		if (saveTimer) return;
		saveTimer = setTimeout(() => {
			saveTimer = null;
			lastSaved = Date.now();
			persistProgress(computeProgress());
		}, SAVE_THROTTLE_MS);
	}

	async function restoreScroll(target: number) {
		if (target < MIN_TRACKED_PROGRESS || target >= 1) return;
		// Wait for the content to be laid out, otherwise scrollHeight is still the empty page.
		await tick();
		await new Promise((resolve) => requestAnimationFrame(resolve));
		const scrollable = document.documentElement.scrollHeight - window.innerHeight;
		if (scrollable <= 0) return;
		window.scrollTo({ top: scrollable * target, behavior: 'auto' });
		progress = target;
		toast('Reprise où tu t’étais arrêté.');
	}

	onMount(() => {
		if (!requireAuth()) return;
		const articleId = page.params.id;
		if (!articleId) {
			error = 'Article introuvable.';
			loading = false;
			return;
		}

		window.addEventListener('scroll', onScroll, { passive: true });

		lumia.article
			.getArticle(articleId)
			.then(async (loaded) => {
				article = loaded;
				saved = false;
				favorite = false;
				markedRead = loaded.read;
				await restoreScroll(loaded.scroll_progress);
			})
			.catch(() => (error = 'Article introuvable.'))
			.finally(() => (loading = false));

		return () => {
			window.removeEventListener('scroll', onScroll);
			if (saveTimer) clearTimeout(saveTimer);
			speech.stop();
			// A last write on the way out, so leaving quickly still records where reading stopped.
			const finalProgress = computeProgress();
			if (finalProgress >= MIN_TRACKED_PROGRESS) persistProgress(finalProgress);
		};
	});
</script>

{#if article}
	<ReadingProgress {progress} />
{/if}

<div class="mx-auto flex w-full flex-col gap-4 pb-24">
	<a
		href="{base}/articles"
		class="flex w-fit items-center gap-1 text-sm text-muted-foreground transition-transform hover:-translate-x-0.5 hover:text-foreground hover:underline"
	>
		<ArrowLeft class="size-4" />
		Retour aux articles
	</a>

	{#if loading}
		<div role="status" aria-label="Chargement de l'article" class="flex flex-col gap-3">
			<Skeleton class="h-72 w-full rounded-2xl sm:h-96" />
			<Skeleton class="h-8 w-3/4" />
			<Skeleton class="h-4 w-40" />
			{#each Array(8)}
				<Skeleton class="h-4 w-full" />
			{/each}
		</div>
	{:else if error}
		<p role="alert" class="text-sm text-destructive">{error}</p>
	{:else if article}
		<Card class="animate-in overflow-hidden fade-in zoom-in-95 slide-in-from-bottom-3 duration-500 ease-out">
			{#if article.image_url}
				<div
					class="relative overflow-hidden"
					style={`view-transition-name: article-image-${article.id};`}
				>
					<img
						src={article.image_url}
						alt=""
						class="h-72 w-full animate-in scale-100 object-cover fade-in zoom-in-110 duration-700 ease-out sm:h-96"
						loading="lazy"
					/>
					<GlareHover class="absolute inset-0" glareColor="#ffffff" glareOpacity={0.3} glareSize={220} />
				</div>
			{/if}
			<CardContent class="pt-6">
				<h1 class="animate-in font-serif text-2xl font-semibold fade-in slide-in-from-bottom-1 duration-500 sm:text-3xl">
					{article.title}
				</h1>
				<div class="mt-1 flex flex-wrap items-center justify-between gap-2">
					<div class="flex items-center gap-3">
						<a
							href={article.url}
							target="_blank"
							rel="noopener"
							class="flex w-fit items-center gap-1 text-sm text-primary hover:underline"
						>
							<ExternalLink class="size-3.5" />
							Lire la source
						</a>
						<span class="flex items-center gap-1 text-sm text-muted-foreground">
							<Clock class="size-3.5" />
							{article.reading_minutes} min de lecture
						</span>
					</div>
					<div class="flex items-center gap-1">
						{#if speech.supported}
							<button
								onclick={toggleSpeech}
								aria-pressed={speech.speaking && !speech.paused}
								class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
							>
								{#if speech.speaking && !speech.paused}
									<Square class="size-4 text-primary" />
									Pause
								{:else}
									<Volume2 class="size-4" />
									{speech.paused ? 'Reprendre' : 'Écouter'}
								{/if}
							</button>
						{/if}
						<button
							onclick={share}
							class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
						>
							{#if linkCopied}
								<Check class="size-4 text-primary" />
								Lien copié
							{:else}
								<Share2 class="size-4" />
								Partager
							{/if}
						</button>
					</div>
				</div>

				<div class="mt-3 flex flex-wrap items-center gap-1.5">
					<a href="{base}/articles?feed_id={article.feed_id}">
						<Badge variant="secondary" class="transition-transform hover:-translate-y-0.5">
							{article.source_label}
						</Badge>
					</a>
					{#if article.author_id && article.author_name}
						<a
							href="{base}/articles?author_id={article.author_id}&author_name={encodeURIComponent(
								article.author_name
							)}"
						>
							<Badge variant="outline" class="transition-transform hover:-translate-y-0.5">
								{article.author_name}
							</Badge>
						</a>
					{/if}
					{#if article.category_id && article.category_name}
						<a
							href="{base}/articles?category_id={article.category_id}&category_name={encodeURIComponent(
								article.category_name
							)}"
						>
							<Badge variant="outline" class="transition-transform hover:-translate-y-0.5">
								{article.category_name}
							</Badge>
						</a>
					{/if}
					{#each article.keywords as keyword (keyword.id)}
						<a
							href="{base}/articles?keyword_id={keyword.id}&keyword_term={encodeURIComponent(
								keyword.term
							)}"
						>
							<Badge
								variant="outline"
								class="flex items-center gap-1 transition-transform hover:-translate-y-0.5"
							>
								<Tag class="size-3" />
								{keyword.term}
							</Badge>
						</a>
					{/each}
				</div>

				<div bind:this={contentEl} class="prose prose-base mt-4 max-w-none">
					{@html sanitizeArticleHtml(article.content)}
				</div>
			</CardContent>
		</Card>

		<div
			class="fixed inset-x-0 z-40 flex justify-center border-t bg-background/90 p-3 backdrop-blur"
			style="bottom: var(--bottom-nav-h, 0px)"
		>
			<div class="flex w-full max-w-3xl gap-1.5 sm:gap-2">
				<Button
					class="flex-1 gap-1.5 px-2 sm:px-4"
					variant={sentiment === 'like' ? 'default' : 'outline'}
					onclick={() => toggleSentiment('like')}
				>
					<ThumbsUp class="size-4 shrink-0" /> <span class="hidden sm:inline">J'aime</span>
				</Button>
				<Button
					class="flex-1 gap-1.5 px-2 sm:px-4"
					variant={sentiment === 'dislike' ? 'default' : 'outline'}
					onclick={() => toggleSentiment('dislike')}
				>
					<ThumbsDown class="size-4 shrink-0" /> <span class="hidden sm:inline">Je n'aime pas</span>
				</Button>
				<Button
					class="flex-1 gap-1.5 px-2 sm:px-4"
					variant={saved ? 'default' : 'outline'}
					onclick={toggleSaved}
				>
					<Bookmark class="size-4 shrink-0" /> <span class="hidden sm:inline">Enregistrer</span>
				</Button>
				<Button
					class="flex-1 gap-1.5 px-2 sm:px-4"
					variant={favorite ? 'default' : 'outline'}
					onclick={toggleFavorite}
				>
					<Star class="size-4 shrink-0" /> <span class="hidden sm:inline">Favoris</span>
				</Button>
				<AddToPlaylist articleId={article.id} />
			</div>
		</div>
	{/if}
</div>
