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
		MagicBento,
		Separator
	} from '@lumia/ui';
	import Upload from '@lucide/svelte/icons/upload';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import FolderPlus from '@lucide/svelte/icons/folder-plus';
	import Rss from '@lucide/svelte/icons/rss';
	import Inbox from '@lucide/svelte/icons/inbox';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Shuffle from '@lucide/svelte/icons/shuffle';
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

	async function removeFeed(feedId: string) {
		await lumia.feed.deleteFeed(feedId);
		if (selectedFeedId === feedId) selectedFeedId = '';
		await load();
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

<div class="flex gap-6">
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
			<p class="text-sm text-destructive">{error}</p>
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
				<CardContent class="flex flex-wrap items-center gap-2">
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
				<CardContent class="flex flex-wrap items-center gap-2">
					<Button onclick={viewArticles}>
						<Newspaper class="size-4" />
						Voir tous les articles du dossier
					</Button>
					<Button variant="secondary" onclick={readInSwipeMode}>
						<Shuffle class="size-4" />
						Mode lecture (swipe)
					</Button>
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
						<form class="flex gap-2" onsubmit={createFolder}>
							<Input type="text" bind:value={newFolderName} placeholder="Nom du dossier" class="max-w-xs" />
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
							<p class="text-sm text-muted-foreground">Chargement…</p>
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
