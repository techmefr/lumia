<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import type { PlaylistDetail } from '@lumia/core';
	import { Button, Card, CardContent, Skeleton, toast } from '@lumia/ui';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Play from '@lucide/svelte/icons/play';
	import Pause from '@lucide/svelte/icons/pause';
	import SkipForward from '@lucide/svelte/icons/skip-forward';
	import SkipBack from '@lucide/svelte/icons/skip-back';
	import Square from '@lucide/svelte/icons/square';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Clock from '@lucide/svelte/icons/clock';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import { SPEECH_FAILURE_MESSAGES, SpeechReader } from '$technical/speech/speech.svelte';

	const RATES = [0.8, 1, 1.25, 1.5];

	let playlist = $state<PlaylistDetail | null>(null);
	let loading = $state(true);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
	let currentIndex = $state(-1);
	let rate = $state(1);

	const speech = new SpeechReader();

	const totalMinutes = $derived(
		(playlist?.articles ?? []).reduce((sum, article) => sum + article.reading_minutes, 0)
	);
	const current = $derived(playlist?.articles[currentIndex] ?? null);

	async function load() {
		loading = true;
		error = null;
		const playlistId = page.params.id;
		if (!playlistId) {
			error = 'playlists.notFound';
			loading = false;
			return;
		}
		try {
			playlist = await lumia.playlist.getPlaylist(playlistId);
		} catch {
			error = 'playlists.notFound';
		} finally {
			loading = false;
		}
	}

	/** Reads an article aloud, then chains to the next one on its own. */
	async function playFrom(index: number) {
		if (!playlist) return;
		const article = playlist.articles[index];
		if (!article) {
			speech.stop();
			currentIndex = -1;
			toast(t('playlists.finishedToast'));
			return;
		}

		currentIndex = index;
		let text = article.summary ?? '';
		try {
			// The list only carries the summary; the body has to be fetched to read it in full.
			const detail = await lumia.article.getArticle(article.id);
			text = new DOMParser().parseFromString(detail.content, 'text/html').body.textContent ?? text;
			await lumia.recommendation.sendFeedback(article.id, { read: true });
		} catch {
			// Fall back on the summary rather than skipping the article silently.
		}

		speech.speak(`${article.title}. ${text}`, {
			rate,
			onDone: () => void playFrom(index + 1)
		});
	}

	// The chain stops on its own when a reading fails, since it advances on the done callback.
	// Without a word on screen, the playlist would just look stuck.
	$effect(() => {
		const failure = speech.error;
		if (failure) toast(t(SPEECH_FAILURE_MESSAGES[failure]));
	});

	function togglePlayback() {
		if (!speech.speaking) {
			void playFrom(currentIndex >= 0 ? currentIndex : 0);
			return;
		}
		if (speech.paused) speech.resume();
		else speech.pause();
	}

	function stop() {
		speech.stop();
		currentIndex = -1;
	}

	function next() {
		void playFrom(currentIndex + 1);
	}

	function previous() {
		void playFrom(Math.max(currentIndex - 1, 0));
	}

	function changeRate(value: number) {
		rate = value;
		speech.setRate(value);
	}

	async function move(index: number, delta: number) {
		if (!playlist) return;
		const ids = playlist.articles.map((article) => article.id);
		const target = index + delta;
		if (target < 0 || target >= ids.length) return;
		[ids[index], ids[target]] = [ids[target], ids[index]];
		try {
			playlist = await lumia.playlist.reorder(playlist.id, ids);
		} catch {
			toast(t('playlists.reorderFailed'), { tone: 'destructive' });
		}
	}

	async function remove(articleId: string) {
		if (!playlist) return;
		try {
			playlist = await lumia.playlist.removeArticle(playlist.id, articleId);
			toast(t('playlists.removedToast'));
		} catch {
			toast(t('playlists.removeFailed'), { tone: 'destructive' });
		}
	}

	onMount(() => {
		if (!requireAuth()) return;
		void load();
		return () => speech.stop();
	});
</script>

<div class="flex flex-col gap-6 pb-28">
	<a
		href="{base}/playlists"
		class="flex w-fit items-center gap-1 text-sm text-muted-foreground transition-transform hover:-translate-x-0.5 hover:text-foreground hover:underline"
	>
		<ArrowLeft class="size-4" />
		{t('playlists.all')}
	</a>

	{#if loading}
		<div role="status" aria-label={t('playlists.loadingOne')} class="flex flex-col gap-3">
			<Skeleton class="h-8 w-56" />
			{#each Array(4)}
				<Skeleton class="h-16 w-full rounded-xl" />
			{/each}
		</div>
	{:else if error}
		<p role="alert" class="text-sm text-destructive">{t(error)}</p>
	{:else if playlist}
		<div class="flex flex-wrap items-baseline justify-between gap-2">
			<h1 class="text-2xl font-semibold">{playlist.name}</h1>
			<span class="flex items-center gap-1.5 text-sm text-muted-foreground">
				<Clock class="size-4" />
				{playlist.articles.length > 1
					? t('playlists.countMany', { count: playlist.articles.length })
					: t('playlists.countOne', { count: playlist.articles.length })} · {t('common.minutes', {
					count: totalMinutes
				})}
			</span>
		</div>

		{#if !speech.supported}
			<p class="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
				{t('playlists.noSpeech')}
			</p>
		{/if}

		{#if playlist.articles.length === 0}
			<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
				<p class="text-sm text-muted-foreground">{t('playlists.detailEmpty')}</p>
				<Button size="sm" href="{base}/articles">{t('common.browseArticles')}</Button>
			</div>
		{:else}
			<ol class="flex flex-col gap-2">
				{#each playlist.articles as article, index (article.id)}
					<li>
						<Card class={index === currentIndex ? 'border-primary' : ''}>
							<CardContent class="flex flex-wrap items-center gap-3 py-3">
								<span class="w-6 shrink-0 text-sm text-muted-foreground">{index + 1}</span>
								<a href="{base}/articles/{article.id}" class="flex min-w-0 flex-1 flex-col gap-0.5">
									<span class="truncate font-medium">{article.title}</span>
									<span class="text-xs text-muted-foreground">
										{article.source_label} · {t('common.minutes', {
											count: article.reading_minutes
										})}
										{#if article.read}· {t('playlists.read')}{/if}
									</span>
								</a>
								<div class="flex items-center gap-0.5">
									<Button size="sm" variant="ghost" onclick={() => playFrom(index)}>
										<Play class="size-4" />
										<span class="sr-only">{t('playlists.listen', { title: article.title })}</span>
									</Button>
									<Button
										size="sm"
										variant="ghost"
										disabled={index === 0}
										onclick={() => move(index, -1)}
									>
										<ChevronUp class="size-4" />
										<span class="sr-only">{t('playlists.moveUp', { title: article.title })}</span>
									</Button>
									<Button
										size="sm"
										variant="ghost"
										disabled={index === playlist.articles.length - 1}
										onclick={() => move(index, 1)}
									>
										<ChevronDown class="size-4" />
										<span class="sr-only">{t('playlists.moveDown', { title: article.title })}</span>
									</Button>
									<Button size="sm" variant="ghost" onclick={() => remove(article.id)}>
										<Trash2 class="size-4" />
										<span class="sr-only">
											{t('playlists.removeArticle', { title: article.title })}
										</span>
									</Button>
								</div>
							</CardContent>
						</Card>
					</li>
				{/each}
			</ol>

			{#if speech.supported}
				<div
					class="fixed inset-x-0 z-40 border-t bg-background/95 p-3 backdrop-blur"
					style="bottom: var(--bottom-nav-h, 0px)"
				>
					<div class="mx-auto flex w-full max-w-3xl flex-col gap-2">
						<div class="flex items-center gap-2">
							<Button variant="outline" size="sm" onclick={previous} disabled={currentIndex <= 0}>
								<SkipBack class="size-4" />
								<span class="sr-only">{t('playlists.previous')}</span>
							</Button>
							<Button onclick={togglePlayback}>
								{#if speech.speaking && !speech.paused}
									<Pause class="size-4" />
									{t('playlists.pause')}
								{:else}
									<Play class="size-4" />
									{speech.paused ? t('playlists.resume') : t('playlists.listenAll')}
								{/if}
							</Button>
							<Button
								variant="outline"
								size="sm"
								onclick={next}
								disabled={currentIndex >= playlist.articles.length - 1}
							>
								<SkipForward class="size-4" />
								<span class="sr-only">{t('playlists.next')}</span>
							</Button>
							{#if speech.speaking}
								<Button variant="ghost" size="sm" onclick={stop}>
									<Square class="size-4" />
									<span class="sr-only">{t('playlists.stop')}</span>
								</Button>
							{/if}

							<fieldset class="ml-auto flex items-center gap-1">
								<legend class="sr-only">{t('playlists.speed')}</legend>
								{#each RATES as value (value)}
									<label
										class="cursor-pointer rounded-md border px-2 py-1 text-xs transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring"
									>
										<input
											type="radio"
											name="speech-rate"
											value={value}
											checked={rate === value}
											onchange={() => changeRate(value)}
											class="sr-only"
										/>
										{value}×
									</label>
								{/each}
							</fieldset>
						</div>

						{#if current}
							<p aria-live="polite" class="truncate text-xs text-muted-foreground">
								{t('playlists.nowPlaying', { title: current.title })}
							</p>
						{/if}
					</div>
				</div>
			{/if}
		{/if}
	{/if}
</div>
