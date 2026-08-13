<script lang="ts">
	import { onMount } from 'svelte';
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
	import { requireAuth } from '$technical/auth/require-auth';

	let playlists = $state<PlaylistSummary[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let newName = $state('');
	let renamingId = $state<string | null>(null);
	let renameValue = $state('');

	async function load() {
		loading = true;
		error = null;
		try {
			playlists = await lumia.playlist.listPlaylists();
		} catch {
			error = 'Impossible de charger les playlists.';
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
			toast(`Playlist « ${name} » créée.`);
		} catch {
			toast('Impossible de créer la playlist.', { tone: 'destructive' });
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
			toast('Impossible de renommer la playlist.', { tone: 'destructive' });
		}
	}

	async function remove(playlist: PlaylistSummary) {
		try {
			await lumia.playlist.deletePlaylist(playlist.id);
			await load();
			toast(`« ${playlist.name} » supprimée.`, {
				action: {
					label: 'Recréer',
					run: async () => {
						await lumia.playlist.createPlaylist(playlist.name);
						await load();
					}
				}
			});
		} catch {
			toast('Impossible de supprimer la playlist.', { tone: 'destructive' });
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-6">
	<h1 class="flex items-center gap-2 text-2xl font-semibold">
		<ListMusic class="size-6 text-primary" />
		Playlists
	</h1>

	<p class="text-sm text-muted-foreground">
		Des files d'articles ordonnées, avec leur durée totale, à lire ou à écouter d'affilée.
	</p>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{error}</p>
	{/if}

	<Card>
		<CardHeader>
			<CardTitle>Nouvelle playlist</CardTitle>
		</CardHeader>
		<CardContent>
			<form class="flex items-end gap-2" onsubmit={create}>
				<div class="flex max-w-xs flex-1 flex-col gap-1.5">
					<Label for="new-playlist">Nom</Label>
					<Input id="new-playlist" bind:value={newName} required placeholder="Trajet du matin" />
				</div>
				<Button type="submit">
					<Plus class="size-4" />
					Créer
				</Button>
			</form>
		</CardContent>
	</Card>

	{#if loading}
		<div role="status" aria-label="Chargement des playlists" class="flex flex-col gap-3">
			{#each Array(3)}
				<Skeleton class="h-20 w-full rounded-2xl" />
			{/each}
		</div>
	{:else if playlists.length === 0}
		<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
			<p class="text-sm text-muted-foreground">
				Aucune playlist. Crée-en une ci-dessus, puis ajoute des articles depuis leur page.
			</p>
			<Button size="sm" href="/articles">Parcourir les articles</Button>
		</div>
	{:else}
		<ul class="flex flex-col gap-3">
			{#each playlists as playlist (playlist.id)}
				<li>
					<Card>
						<CardContent class="flex flex-wrap items-center justify-between gap-3 py-4">
							{#if renamingId === playlist.id}
								<form class="flex flex-1 items-end gap-2" onsubmit={confirmRename}>
									<div class="flex max-w-xs flex-1 flex-col gap-1.5">
										<Label for="rename-{playlist.id}">Nouveau nom</Label>
										<Input id="rename-{playlist.id}" bind:value={renameValue} required />
									</div>
									<Button type="submit" size="sm">Renommer</Button>
									<Button
										type="button"
										size="sm"
										variant="ghost"
										onclick={() => (renamingId = null)}
									>
										Annuler
									</Button>
								</form>
							{:else}
								<a href="/playlists/{playlist.id}" class="flex min-w-0 flex-1 flex-col gap-0.5">
									<span class="truncate font-medium">{playlist.name}</span>
									<span class="flex items-center gap-2 text-xs text-muted-foreground">
										{playlist.item_count} article{playlist.item_count > 1 ? 's' : ''}
										{#if playlist.total_reading_minutes > 0}
											<span class="flex items-center gap-1">
												<Clock class="size-3" />
												{playlist.total_reading_minutes} min
											</span>
										{/if}
									</span>
								</a>
								<div class="flex items-center gap-1">
									<Button size="sm" variant="ghost" onclick={() => startRename(playlist)}>
										<Pencil class="size-4" />
										<span class="sr-only">Renommer {playlist.name}</span>
									</Button>
									<Button size="sm" variant="ghost" onclick={() => remove(playlist)}>
										<Trash2 class="size-4" />
										<span class="sr-only">Supprimer {playlist.name}</span>
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
