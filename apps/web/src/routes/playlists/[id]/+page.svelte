<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import type { PlaylistDetail } from '@lumia/core';
	import { Button, Card, CardContent, Skeleton, toast } from '@lumia/ui';
	import ArrowLeft from '@lucide/svelte/icons/arrow-left';
	import Play from '@lucide/svelte/icons/play';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Clock from '@lucide/svelte/icons/clock';
	import ExportPlaylistButton from '$domain/playlist/export-playlist-button.svelte';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import { player } from '$domain/audio/audio-player.svelte';

	let playlist = $state<PlaylistDetail | null>(null);
	let loading = $state(true);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);

	const totalMinutes = $derived(
		(playlist?.articles ?? []).reduce((sum, article) => sum + article.reading_minutes, 0)
	);

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

	function playFrom(index: number) {
		if (playlist) void player.play(playlist.articles, index);
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
	});
</script>

<div class="flex flex-col gap-6 pb-6">
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
			<ExportPlaylistButton playlistId={playlist.id} name={playlist.name} />
			<span class="flex items-center gap-1.5 text-sm text-muted-foreground">
				<Clock class="size-4" />
				{playlist.articles.length > 1
					? t('playlists.countMany', { count: playlist.articles.length })
					: t('playlists.countOne', { count: playlist.articles.length })} · {t('common.minutes', {
					count: totalMinutes
				})}
			</span>
		</div>

		{#if player.supported && playlist.articles.length > 0}
			<div>
				<Button data-test-listen-all onclick={() => playFrom(0)}>
					<Play class="size-4" />
					{t('playlists.listenAll')}
				</Button>
			</div>
		{/if}

		{#if !player.supported}
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
						<Card class={player.current?.id === article.id ? 'border-primary' : ''}>
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

		{/if}
	{/if}
</div>
