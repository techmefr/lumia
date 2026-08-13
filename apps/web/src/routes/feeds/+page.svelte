<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Feed, Folder } from '@lumia/core';
	import {
		Badge,
		Button,
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
		Input,
		Label,
		MagicBento,
		Separator
	} from '@lumia/ui';
	import Upload from '@lucide/svelte/icons/upload';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import FolderPlus from '@lucide/svelte/icons/folder-plus';
	import Plus from '@lucide/svelte/icons/plus';
	import Rss from '@lucide/svelte/icons/rss';
	import Inbox from '@lucide/svelte/icons/inbox';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Shuffle from '@lucide/svelte/icons/shuffle';
	import Pencil from '@lucide/svelte/icons/pencil';
	import { toast } from '@lumia/ui';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { resolveFolderName } from '$domain/feed/resolve-folder-name';
	import FeedSidebar from '$domain/feed/feed-sidebar.svelte';

	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let loading = $state(true);
	let importing = $state(false);
	let error = $state<string | null>(null);
	let newFolderName = $state('');
	let selectedFolderId = $state('');
	let selectedFeedId = $state('');
	let newFeedUrl = $state('');
	let newFeedFolderId = $state('');
	let addingFeed = $state(false);
	let addFeedError = $state<string | null>(null);
	let renamingFolderId = $state<string | null>(null);
	let folderRenameValue = $state('');
	let renamingFeedId = $state<string | null>(null);
	let feedRenameValue = $state('');

	const selectedFolder = $derived(folders.find((f) => f.id === selectedFolderId) ?? null);
	const selectedFeed = $derived(feeds.find((f) => f.id === selectedFeedId) ?? null);
	const feedsInSelectedFolder = $derived(
		selectedFolderId ? feeds.filter((feed) => feed.folder_id === selectedFolderId) : []
	);

	async function load() {
		loading = true;
		error = null;
		try {
			[folders, feeds] = await Promise.all([lumia.feed.listFolders(), lumia.feed.listFeeds()]);
		} catch {
			error = 'Impossible de charger tes flux.';
		} finally {
			loading = false;
		}
	}

	async function createFolder(event: SubmitEvent) {
		event.preventDefault();
		if (!newFolderName.trim()) return;
		await lumia.feed.createFolder(newFolderName.trim());
		newFolderName = '';
		await load();
	}

	async function addFeed(event: SubmitEvent) {
		event.preventDefault();
		if (!newFeedUrl.trim()) return;

		addingFeed = true;
		addFeedError = null;
		try {
			await lumia.feed.addFeedByUrl(newFeedUrl.trim(), newFeedFolderId || null);
			newFeedUrl = '';
			newFeedFolderId = '';
			await load();
		} catch {
			addFeedError = 'Impossible d’ajouter ce flux — vérifie l’URL.';
		} finally {
			addingFeed = false;
		}
	}

	async function removeFeed(feedId: string) {
		const feed = feeds.find((candidate) => candidate.id === feedId);
		await lumia.feed.deleteFeed(feedId);
		if (selectedFeedId === feedId) selectedFeedId = '';
		await load();
		toast(`« ${feed?.title ?? 'Flux'} » retiré.`, {
			action:
				feed && feed.source_type === 'miniflux'
					? {
							label: 'Rétablir',
							run: async () => {
								await lumia.feed.addFeedByUrl(feed.url, feed.folder_id);
								await load();
							}
						}
					: undefined
		});
	}

	async function renameFolder(event: SubmitEvent) {
		event.preventDefault();
		const name = folderRenameValue.trim();
		if (!renamingFolderId || !name) return;
		try {
			await lumia.feed.renameFolder(renamingFolderId, name);
			renamingFolderId = null;
			await load();
		} catch {
			toast('Impossible de renommer ce dossier.', { tone: 'destructive' });
		}
	}

	async function removeFolder(folder: Folder) {
		try {
			await lumia.feed.deleteFolder(folder.id);
			if (selectedFolderId === folder.id) selectedFolderId = '';
			await load();
			// Deleting a folder never deletes its feeds, so the undo only has to recreate the folder
			// and refile what used to be in it.
			const previousFeedIds = feeds
				.filter((feed) => feed.folder_id === folder.id)
				.map((feed) => feed.id);
			toast(`Dossier « ${folder.name} » supprimé, ses flux sont conservés.`, {
				action: {
					label: 'Annuler',
					run: async () => {
						const recreated = await lumia.feed.createFolder(folder.name);
						for (const feedId of previousFeedIds) {
							await lumia.feed.updateFeed(feedId, { folder_id: recreated.id });
						}
						await load();
					}
				}
			});
		} catch {
			toast('Impossible de supprimer ce dossier.', { tone: 'destructive' });
		}
	}

	async function moveFeed(feedId: string, folderId: string) {
		try {
			await lumia.feed.updateFeed(feedId, { folder_id: folderId || null });
			await load();
			toast('Flux déplacé.');
		} catch {
			toast('Impossible de déplacer ce flux.', { tone: 'destructive' });
		}
	}

	async function retitleFeed(event: SubmitEvent) {
		event.preventDefault();
		const title = feedRenameValue.trim();
		if (!renamingFeedId || !title) return;
		try {
			await lumia.feed.updateFeed(renamingFeedId, { title });
			renamingFeedId = null;
			await load();
		} catch {
			toast('Impossible de renommer ce flux.', { tone: 'destructive' });
		}
	}

	async function importOpml(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		importing = true;
		error = null;
		try {
			await lumia.feed.importOpml(file);
			await load();
		} catch {
			error = "Import OPML impossible — vérifie que le fichier est bien un export Feedly.";
		} finally {
			importing = false;
			input.value = '';
		}
	}

	function selectAll() {
		selectedFolderId = '';
		selectedFeedId = '';
	}

	function selectFolder(folderId: string) {
		selectedFolderId = selectedFolderId === folderId ? '' : folderId;
		selectedFeedId = '';
	}

	function selectFeed(feedId: string) {
		selectedFeedId = selectedFeedId === feedId ? '' : feedId;
		selectedFolderId = '';
	}

	function viewArticles() {
		if (selectedFeedId) void goto(`/articles?feed_id=${selectedFeedId}`);
		else if (selectedFolderId) void goto(`/articles?folder_id=${selectedFolderId}`);
	}

	function readInSwipeMode() {
		if (selectedFeedId) {
			const label = encodeURIComponent(selectedFeed?.title ?? '');
			void goto(`/lire?feed_id=${selectedFeedId}&label=${label}`);
		} else if (selectedFolderId) {
			const label = encodeURIComponent(selectedFolder?.name ?? '');
			void goto(`/lire?folder_id=${selectedFolderId}&label=${label}`);
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-4 sm:flex-row sm:gap-6">
	<FeedSidebar
		{folders}
		{feeds}
		{selectedFolderId}
		{selectedFeedId}
		onSelectAll={selectAll}
		onSelectFolder={selectFolder}
		onSelectFeed={selectFeed}
	/>

	<div class="flex min-w-0 flex-1 flex-col gap-6">
		<h1 class="text-2xl font-semibold">Mes flux</h1>

		{#if error}
			<p role="alert" class="text-sm text-destructive">{error}</p>
		{/if}

		{#if selectedFeed}
			<Card>
				<CardHeader>
					<CardTitle class="flex items-center gap-2">
						<Rss class="size-4 text-primary" />
						{selectedFeed.title}
					</CardTitle>
					<CardDescription>
						<a href={selectedFeed.url} target="_blank" rel="noopener" class="hover:underline">
							{selectedFeed.url}
						</a>
					</CardDescription>
				</CardHeader>
				<CardContent class="flex flex-col gap-4">
					<div class="flex flex-wrap items-center gap-2">
						<Button onclick={viewArticles}>
							<Newspaper class="size-4" />
							Voir les articles
						</Button>
						<Button variant="secondary" onclick={readInSwipeMode}>
							<Shuffle class="size-4" />
							Mode lecture (swipe)
						</Button>
						<Button variant="ghost" onclick={() => removeFeed(selectedFeed!.id)}>
							<Trash2 class="size-4" />
							Retirer ce flux
						</Button>
					</div>

					<Separator />

					<div class="flex flex-wrap items-end gap-4">
						{#if renamingFeedId === selectedFeed.id}
							<form class="flex items-end gap-2" onsubmit={retitleFeed}>
								<div class="flex flex-col gap-1.5">
									<Label for="feed-title">Nom du flux</Label>
									<Input id="feed-title" bind:value={feedRenameValue} required />
								</div>
								<Button type="submit" size="sm">Renommer</Button>
								<Button
									type="button"
									size="sm"
									variant="ghost"
									onclick={() => (renamingFeedId = null)}
								>
									Annuler
								</Button>
							</form>
						{:else}
							<Button
								size="sm"
								variant="outline"
								onclick={() => {
									renamingFeedId = selectedFeed!.id;
									feedRenameValue = selectedFeed!.title;
								}}
							>
								<Pencil class="size-4" />
								Renommer
							</Button>
						{/if}

						<div class="flex flex-col gap-1.5">
							<Label for="feed-folder">Dossier</Label>
							<select
								id="feed-folder"
								value={selectedFeed.folder_id ?? ''}
								onchange={(event) => moveFeed(selectedFeed!.id, event.currentTarget.value)}
								class="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
							>
								<option value="">Sans dossier</option>
								{#each folders as folder (folder.id)}
									<option value={folder.id}>{folder.name}</option>
								{/each}
							</select>
						</div>
					</div>
				</CardContent>
			</Card>
		{:else if selectedFolder}
			<Card>
				<CardHeader>
					<CardTitle>{selectedFolder.name}</CardTitle>
					<CardDescription>
						{feedsInSelectedFolder.length} flux dans ce dossier.
					</CardDescription>
				</CardHeader>
				<CardContent class="flex flex-col gap-4">
					<div class="flex flex-wrap items-center gap-2">
						<Button onclick={viewArticles}>
							<Newspaper class="size-4" />
							Voir tous les articles du dossier
						</Button>
						<Button variant="secondary" onclick={readInSwipeMode}>
							<Shuffle class="size-4" />
							Mode lecture (swipe)
						</Button>
					</div>

					<Separator />

					{#if renamingFolderId === selectedFolder.id}
						<form class="flex items-end gap-2" onsubmit={renameFolder}>
							<div class="flex max-w-xs flex-1 flex-col gap-1.5">
								<Label for="folder-name">Nom du dossier</Label>
								<Input id="folder-name" bind:value={folderRenameValue} required />
							</div>
							<Button type="submit" size="sm">Renommer</Button>
							<Button
								type="button"
								size="sm"
								variant="ghost"
								onclick={() => (renamingFolderId = null)}
							>
								Annuler
							</Button>
						</form>
					{:else}
						<div class="flex flex-wrap items-center gap-2">
							<Button
								size="sm"
								variant="outline"
								onclick={() => {
									renamingFolderId = selectedFolder!.id;
									folderRenameValue = selectedFolder!.name;
								}}
							>
								<Pencil class="size-4" />
								Renommer le dossier
							</Button>
							<Button size="sm" variant="ghost" onclick={() => removeFolder(selectedFolder!)}>
								<Trash2 class="size-4" />
								Supprimer le dossier
							</Button>
							<span class="text-xs text-muted-foreground">
								Les flux du dossier sont conservés, ils passent simplement « sans dossier ».
							</span>
						</div>
					{/if}
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle>Flux du dossier</CardTitle>
				</CardHeader>
				<CardContent>
					{#if feedsInSelectedFolder.length === 0}
						<p class="flex items-center gap-2 text-sm text-muted-foreground">
							<Inbox class="size-4" />
							Aucun flux dans ce dossier.
						</p>
					{:else}
						<div class="flex flex-col">
							{#each feedsInSelectedFolder as feed, index (feed.id)}
								{#if index > 0}<Separator />{/if}
								<button
									onclick={() => selectFeed(feed.id)}
									class="flex items-center justify-between gap-4 py-3 text-left"
								>
									<div class="flex items-center gap-3">
										<Rss class="size-4 shrink-0 text-primary" />
										<span class="font-medium">{feed.title}</span>
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</CardContent>
			</Card>
		{:else}
			<MagicBento class="grid-cols-1 sm:grid-cols-2">
				<Card class="magic-bento-cell sm:col-span-2">
					<CardHeader>
						<CardTitle>Ajouter un flux</CardTitle>
						<CardDescription>Colle l’URL RSS/Atom d’un site pour t’y abonner.</CardDescription>
					</CardHeader>
					<CardContent>
						{#if addFeedError}
							<p role="alert" class="mb-2 text-sm text-destructive">{addFeedError}</p>
						{/if}
						<form class="flex flex-wrap items-end gap-2" onsubmit={addFeed}>
							<div class="flex max-w-sm flex-1 flex-col gap-1.5">
								<Label for="new-feed-url">URL du flux</Label>
								<Input
									id="new-feed-url"
									type="url"
									bind:value={newFeedUrl}
									placeholder="https://exemple.com/feed.xml"
									required
									disabled={addingFeed}
								/>
							</div>
							<div class="flex flex-col gap-1.5">
								<Label for="new-feed-folder">Dossier</Label>
								<select
									id="new-feed-folder"
									bind:value={newFeedFolderId}
									disabled={addingFeed}
									class="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
								>
									<option value="">Sans dossier</option>
									{#each folders as folder (folder.id)}
										<option value={folder.id}>{folder.name}</option>
									{/each}
								</select>
							</div>
							<Button type="submit" disabled={addingFeed}>
								<Plus class="size-4" />
								{addingFeed ? 'Ajout…' : 'Ajouter'}
							</Button>
						</form>
					</CardContent>
				</Card>

				<Card class="magic-bento-cell">
					<CardHeader>
						<CardTitle>Importer depuis Feedly</CardTitle>
						<CardDescription>Exporte tes flux en OPML depuis Feedly, puis importe le fichier ici.</CardDescription>
					</CardHeader>
					<CardContent>
						<label
							class="flex w-fit cursor-pointer items-center gap-2 rounded-md border border-dashed border-input px-4 py-2 text-sm hover:bg-accent"
						>
							<Upload class="size-4" />
							{importing ? 'Import en cours…' : 'Choisir un fichier .opml'}
							<input
								type="file"
								accept=".opml,.xml,text/xml"
								disabled={importing}
								onchange={importOpml}
								class="hidden"
							/>
						</label>
					</CardContent>
				</Card>

				<Card class="magic-bento-cell">
					<CardHeader>
						<CardTitle>Nouveau dossier</CardTitle>
					</CardHeader>
					<CardContent>
						<form class="flex items-end gap-2" onsubmit={createFolder}>
							<div class="flex max-w-xs flex-1 flex-col gap-1.5">
								<Label for="new-folder-name">Nom du dossier</Label>
								<Input id="new-folder-name" type="text" bind:value={newFolderName} required />
							</div>
							<Button type="submit" variant="secondary">
								<FolderPlus class="size-4" />
								Créer
							</Button>
						</form>
					</CardContent>
				</Card>

				<Card class="magic-bento-cell sm:col-span-2">
					<CardHeader>
						<CardTitle>Flux abonnés</CardTitle>
					</CardHeader>
					<CardContent>
						{#if loading}
							<p role="status" class="text-sm text-muted-foreground">Chargement…</p>
						{:else if feeds.length === 0}
							<p class="flex items-center gap-2 text-sm text-muted-foreground">
								<Inbox class="size-4" />
								Aucun flux pour le moment.
							</p>
						{:else}
							<div class="flex flex-col">
								{#each feeds as feed, index (feed.id)}
									{#if index > 0}<Separator />{/if}
									<div
										class="flex animate-in items-center justify-between gap-4 py-3 fade-in slide-in-from-left-1 duration-300"
										style={`animation-delay: ${index * 40}ms`}
									>
										<div class="flex items-center gap-3">
											<Rss class="size-4 shrink-0 text-primary" />
											<div class="flex flex-col gap-1">
												<span class="font-medium">{feed.title}</span>
												<a href={feed.url} target="_blank" rel="noopener" class="text-xs text-muted-foreground hover:underline">
													{feed.url}
												</a>
											</div>
										</div>
										<div class="flex items-center gap-3">
											<Badge variant="secondary">{resolveFolderName(folders, feed.folder_id)}</Badge>
											<Button variant="ghost" size="icon" onclick={() => removeFeed(feed.id)}>
												<Trash2 class="size-4" />
											</Button>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</CardContent>
				</Card>
			</MagicBento>
		{/if}
	</div>
</div>
