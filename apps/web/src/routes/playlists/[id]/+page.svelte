<script lang="ts">
	import { base } from '$technical/paths/base';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import type { PlaylistDetail } from '@lumia/core';
	import { Badge, Button, Card, CardContent, Skeleton, toast, Icon } from '@lumia/ui';
	import { ArrowDown01Icon, ArrowLeft02Icon, ArrowUp01Icon, Clock01Icon, Delete02Icon, PlayIcon, PrinterIcon } from '@hugeicons/core-free-icons';
	import ExportPlaylistButton from '$domain/playlist/export-playlist-button.svelte';
	import PlaylistSharing from '../../../../domain/playlist/playlist-sharing.svelte';
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
	const canEdit = $derived(playlist?.role === 'owner' || playlist?.role === 'editor');
	const addedBy = $derived(
		new Map((playlist?.authorship ?? []).map((item) => [item.article_id, item.added_by]))
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
		class="flex w-fit items-center gap-1 text-sm text-muted-foreground transition-transform hover:-translate-x-0.5 hover:text-foreground hover:underline print:hidden"
	>
		<Icon icon={ArrowLeft02Icon} class="size-4" />
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
			<h1 class="text-2xl font-semibold">
				{playlist.name}
				{#if playlist.role !== 'owner'}
					<Badge data-test-role={playlist.role} variant="secondary" class="ml-2 align-middle">
						{t(playlist.role === 'editor' ? 'playlists.roleEditor' : 'playlists.roleViewer')}
					</Badge>
				{/if}
			</h1>
			<div class="flex flex-wrap items-center gap-2 print:hidden">
				<ExportPlaylistButton playlistId={playlist.id} name={playlist.name} />
				<button
					type="button"
					data-test-print-button
					onclick={() => window.print()}
					class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
				>
					<Icon icon={PrinterIcon} class="size-4" />
					{t('print.button')}
				</button>
			</div>
			<span class="flex items-center gap-1.5 text-sm text-muted-foreground">
				<Icon icon={Clock01Icon} class="size-4" />
				{playlist.articles.length > 1
					? t('playlists.countMany', { count: playlist.articles.length })
					: t('playlists.countOne', { count: playlist.articles.length })} · {t('common.minutes', {
					count: totalMinutes
				})}
			</span>
		</div>

		{#if player.supported && playlist.articles.length > 0}
			<div class="print:hidden">
				<Button data-test-listen-all onclick={() => playFrom(0)}>
					<Icon icon={PlayIcon} class="size-4" />
					{t('playlists.listenAll')}
				</Button>
			</div>
		{/if}

		{#if !player.supported}
			<p class="rounded-lg border border-dashed p-3 text-sm text-muted-foreground print:hidden">
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
						<Card
							class="{player.current?.id === article.id ? 'border-primary' : ''} print:border-0 print:shadow-none"
						>
							<CardContent class="flex flex-wrap items-center gap-3 py-3">
								<span class="w-6 shrink-0 text-sm text-muted-foreground">{index + 1}</span>
								<a href="{base}/articles/{article.id}" class="flex min-w-0 flex-1 flex-col gap-0.5">
									<span class="truncate font-medium print:whitespace-normal">{article.title}</span>
									<span class="text-xs text-muted-foreground">
										{article.source_label} · {t('common.minutes', {
											count: article.reading_minutes
										})}
										{#if article.read}· {t('playlists.read')}{/if}
										{#if addedBy.get(article.id)}
											<span data-test-added-by>
												· {t('playlists.addedBy', { name: addedBy.get(article.id) ?? '' })}
											</span>
										{/if}
									</span>
								</a>
								<div class="flex items-center gap-0.5 print:hidden">
									<Button size="sm" variant="ghost" onclick={() => playFrom(index)}>
										<Icon icon={PlayIcon} class="size-4" />
										<span class="sr-only">{t('playlists.listen', { title: article.title })}</span>
									</Button>
									{#if canEdit}
									<Button
										size="sm"
										variant="ghost"
										disabled={index === 0}
										onclick={() => move(index, -1)}
									>
										<Icon icon={ArrowUp01Icon} class="size-4" />
										<span class="sr-only">{t('playlists.moveUp', { title: article.title })}</span>
									</Button>
									<Button
										size="sm"
										variant="ghost"
										disabled={index === playlist.articles.length - 1}
										onclick={() => move(index, 1)}
									>
										<Icon icon={ArrowDown01Icon} class="size-4" />
										<span class="sr-only">{t('playlists.moveDown', { title: article.title })}</span>
									</Button>
									<Button size="sm" variant="ghost" onclick={() => remove(article.id)}>
										<Icon icon={Delete02Icon} class="size-4" />
										<span class="sr-only">
											{t('playlists.removeArticle', { title: article.title })}
										</span>
									</Button>
									{/if}
								</div>
							</CardContent>
						</Card>
					</li>
				{/each}
			</ol>

		{/if}

		<div class="print:hidden">
			<PlaylistSharing
				playlistId={playlist.id}
				role={playlist.role}
				onleave={() => goto(`${base}/playlists`)}
			/>
		</div>
	{/if}
</div>
