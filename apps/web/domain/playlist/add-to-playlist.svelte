<script lang="ts">
	import type { PlaylistSummary } from '@lumia/core';
	import { Button, Input, toast } from '@lumia/ui';
	import ListPlus from '@lucide/svelte/icons/list-plus';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articleId: string;
	}

	let { articleId }: Props = $props();

	let open = $state(false);
	let playlists = $state<PlaylistSummary[]>([]);
	let loading = $state(false);
	let newName = $state('');
	let container = $state<HTMLElement | null>(null);

	async function load() {
		loading = true;
		try {
			playlists = await lumia.playlist.listPlaylists();
		} catch {
			toast(t('playlists.loadFailed'), { tone: 'destructive' });
		} finally {
			loading = false;
		}
	}

	async function openPanel() {
		open = !open;
		if (open && playlists.length === 0) await load();
	}

	async function addTo(playlist: PlaylistSummary) {
		try {
			await lumia.playlist.addArticle(playlist.id, articleId);
			open = false;
			toast(t('addToPlaylist.addedToast', { name: playlist.name }));
		} catch {
			toast(t('addToPlaylist.addFailed'), { tone: 'destructive' });
		}
	}

	async function createAndAdd(event: SubmitEvent) {
		event.preventDefault();
		const name = newName.trim();
		if (!name) return;
		try {
			const created = await lumia.playlist.createPlaylist(name);
			await lumia.playlist.addArticle(created.id, articleId);
			newName = '';
			open = false;
			toast(t('playlists.createdToast', { name }));
		} catch {
			toast(t('playlists.createFailed'), { tone: 'destructive' });
		}
	}

	$effect(() => {
		if (!open) return;
		function onPointerDown(event: PointerEvent) {
			if (container && !container.contains(event.target as Node)) open = false;
		}
		document.addEventListener('pointerdown', onPointerDown);
		return () => document.removeEventListener('pointerdown', onPointerDown);
	});
</script>

<div bind:this={container} class="relative flex-1">
	<Button
		class="w-full gap-1.5 px-2 sm:px-4"
		variant="outline"
		onclick={openPanel}
		aria-expanded={open}
	>
		<ListPlus class="size-4 shrink-0" />
		<span class="hidden sm:inline">{t('addToPlaylist.button')}</span>
	</Button>

	{#if open}
		<div
			class="absolute bottom-full left-0 z-50 mb-2 w-64 rounded-xl border bg-card p-2 shadow-xl"
		>
			{#if loading}
				<p role="status" class="px-2 py-1.5 text-sm text-muted-foreground">{t('common.loading')}</p>
			{:else if playlists.length === 0}
				<p class="px-2 py-1.5 text-sm text-muted-foreground">{t('addToPlaylist.empty')}</p>
			{:else}
				<ul class="flex max-h-48 flex-col overflow-y-auto">
					{#each playlists as playlist (playlist.id)}
						<li>
							<button
								onclick={() => addTo(playlist)}
								class="flex min-h-10 w-full items-center justify-between gap-2 rounded-md px-2 text-left text-sm transition-colors hover:bg-secondary"
							>
								<span class="truncate">{playlist.name}</span>
								<span class="shrink-0 text-xs text-muted-foreground">
									{playlist.item_count}
								</span>
							</button>
						</li>
					{/each}
				</ul>
			{/if}

			<form class="mt-2 flex gap-1.5 border-t pt-2" onsubmit={createAndAdd}>
				<label for="new-playlist-name" class="sr-only">{t('addToPlaylist.newLabel')}</label>
				<Input
					id="new-playlist-name"
					bind:value={newName}
					placeholder={t('addToPlaylist.newLabel')}
					required
				/>
				<Button type="submit" size="sm" variant="secondary">{t('addToPlaylist.create')}</Button>
			</form>
		</div>
	{/if}
</div>
