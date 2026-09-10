<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { PlaylistSummary } from '@lumia/core';
	import {
		Button,
		Card,
		CardContent,
		CardHeader,
		CardTitle,
		Input,
		Label,
		Skeleton,
		toast
	} from '@lumia/ui';
	import ListMusic from '@lucide/svelte/icons/list-music';
	import Plus from '@lucide/svelte/icons/plus';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Clock from '@lucide/svelte/icons/clock';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';

	let playlists = $state<PlaylistSummary[]>([]);
	let loading = $state(true);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
	let newName = $state('');
	let renamingId = $state<string | null>(null);
	let renameValue = $state('');
	let filling = $state<number | null>(null);

	/** The three durations the design settled on: a coffee, a commute, a long train leg. */
	const TIME_OPTIONS = [12, 25, 45];

	async function fillForDuration(minutes: number) {
		filling = minutes;
		try {
			const playlist = await lumia.playlist.createPlaylistForDuration(minutes);
			await load();
			if (playlist.articles.length === 0) {
				toast(t('playlists.nothingShortEnough'), { tone: 'destructive' });
				return;
			}
			toast(t('playlists.filledToast', { count: playlist.articles.length, minutes }), {
				action: { label: t('common.open'), run: () => goto(`${base}/playlists/${playlist.id}`) }
			});
		} catch {
			toast(t('playlists.fillFailed'), { tone: 'destructive' });
		} finally {
			filling = null;
		}
	}

	async function load() {
		loading = true;
		error = null;
		try {
			playlists = await lumia.playlist.listPlaylists();
		} catch {
			error = 'playlists.loadFailed';
		} finally {
			loading = false;
		}
	}

	async function create(event: SubmitEvent) {
		event.preventDefault();
		const name = newName.trim();
		if (!name) return;
		try {
			await lumia.playlist.createPlaylist(name);
			newName = '';
			await load();
			toast(t('playlists.createdToast', { name }));
		} catch {
			toast(t('playlists.createFailed'), { tone: 'destructive' });
		}
	}

	function startRename(playlist: PlaylistSummary) {
		renamingId = playlist.id;
		renameValue = playlist.name;
	}

	async function confirmRename(event: SubmitEvent) {
		event.preventDefault();
		const name = renameValue.trim();
		if (!renamingId || !name) return;
		try {
			await lumia.playlist.renamePlaylist(renamingId, name);
			renamingId = null;
			await load();
		} catch {
			toast(t('playlists.renameFailed'), { tone: 'destructive' });
		}
	}

	async function remove(playlist: PlaylistSummary) {
		try {
			await lumia.playlist.deletePlaylist(playlist.id);
			await load();
			toast(t('playlists.deletedToast', { name: playlist.name }), {
				action: {
					label: t('playlists.recreate'),
					run: async () => {
						await lumia.playlist.createPlaylist(playlist.name);
						await load();
					}
				}
			});
		} catch {
			toast(t('playlists.deleteFailed'), { tone: 'destructive' });
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-6">
	<h1 class="flex items-center gap-2 text-2xl font-semibold">
		<ListMusic class="size-6 text-primary" />
		{t('playlists.title')}
	</h1>

	<p class="text-sm text-muted-foreground">{t('playlists.intro')}</p>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{t(error)}</p>
	{/if}

	<Card>
		<CardHeader>
			<CardTitle>{t('playlists.byTimeTitle')}</CardTitle>
		</CardHeader>
		<CardContent class="flex flex-col gap-2">
			<p class="text-sm text-muted-foreground">{t('playlists.byTimeHint')}</p>
			<div class="flex flex-wrap gap-2">
				{#each TIME_OPTIONS as minutes (minutes)}
					<Button
						variant="secondary"
						onclick={() => fillForDuration(minutes)}
						disabled={filling !== null}
					>
						<Clock class="size-4" />
						{filling === minutes
							? t('playlists.composing')
							: t('common.minutes', { count: minutes })}
					</Button>
				{/each}
			</div>
		</CardContent>
	</Card>

	<Card>
		<CardHeader>
			<CardTitle>{t('playlists.newTitle')}</CardTitle>
		</CardHeader>
		<CardContent>
			<form class="flex items-end gap-2" onsubmit={create}>
				<div class="flex max-w-xs flex-1 flex-col gap-1.5">
					<Label for="new-playlist">{t('playlists.nameLabel')}</Label>
					<Input
						id="new-playlist"
						bind:value={newName}
						required
						placeholder={t('playlists.namePlaceholder')}
					/>
				</div>
				<Button type="submit">
					<Plus class="size-4" />
					{t('feeds.create')}
				</Button>
			</form>
		</CardContent>
	</Card>

	{#if loading}
		<div role="status" aria-label={t('playlists.loading')} class="flex flex-col gap-3">
			{#each Array(3)}
				<Skeleton class="h-20 w-full rounded-2xl" />
			{/each}
		</div>
	{:else if playlists.length === 0}
		<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
			<p class="text-sm text-muted-foreground">{t('playlists.empty')}</p>
			<Button size="sm" href="{base}/articles">{t('common.browseArticles')}</Button>
		</div>
	{:else}
		<!-- Columns rather than rows stretched across the display: a playlist is a name and a count,
		     and a wide screen has room for several of them side by side. -->
		<ul data-test-playlist-columns class="grid grid-cols-1 gap-3 lg:grid-cols-2 2xl:grid-cols-3">
			{#each playlists as playlist (playlist.id)}
				<li>
					<Card>
						<CardContent class="flex flex-wrap items-center justify-between gap-3 py-4">
							{#if renamingId === playlist.id}
								<form class="flex flex-1 items-end gap-2" onsubmit={confirmRename}>
									<div class="flex max-w-xs flex-1 flex-col gap-1.5">
										<Label for="rename-{playlist.id}">{t('playlists.newName')}</Label>
										<Input id="rename-{playlist.id}" bind:value={renameValue} required />
									</div>
									<Button type="submit" size="sm">{t('common.rename')}</Button>
									<Button
										type="button"
										size="sm"
										variant="ghost"
										onclick={() => (renamingId = null)}
									>
										{t('common.cancel')}
									</Button>
								</form>
							{:else}
								<a href="{base}/playlists/{playlist.id}" class="flex min-w-0 flex-1 flex-col gap-0.5">
									<span class="truncate font-medium">{playlist.name}</span>
									<span class="flex items-center gap-2 text-xs text-muted-foreground">
										{playlist.item_count > 1
											? t('playlists.countMany', { count: playlist.item_count })
											: t('playlists.countOne', { count: playlist.item_count })}
										{#if playlist.total_reading_minutes > 0}
											<span class="flex items-center gap-1">
												<Clock class="size-3" />
												{t('common.minutes', { count: playlist.total_reading_minutes })}
											</span>
										{/if}
									</span>
								</a>
								<div class="flex items-center gap-1">
									<Button size="sm" variant="ghost" onclick={() => startRename(playlist)}>
										<Pencil class="size-4" />
										<span class="sr-only">{t('playlists.renameOne', { name: playlist.name })}</span>
									</Button>
									<Button size="sm" variant="ghost" onclick={() => remove(playlist)}>
										<Trash2 class="size-4" />
										<span class="sr-only">{t('playlists.deleteOne', { name: playlist.name })}</span>
									</Button>
								</div>
							{/if}
						</CardContent>
					</Card>
				</li>
			{/each}
		</ul>
	{/if}
</div>
