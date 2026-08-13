<script lang="ts">
	import { onMount } from 'svelte';
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
		Separator
	} from '@lumia/ui';
	import Upload from '@lucide/svelte/icons/upload';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import FolderPlus from '@lucide/svelte/icons/folder-plus';
	import Rss from '@lucide/svelte/icons/rss';
	import Inbox from '@lucide/svelte/icons/inbox';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import { resolveFolderName } from '$domain/feed/resolve-folder-name';

	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let loading = $state(true);
	let importing = $state(false);
	let error = $state<string | null>(null);
	let newFolderName = $state('');

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

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-6">
	<h1 class="text-2xl font-semibold">Mes flux</h1>

	<Card>
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

	<Card>
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

	{#if error}
		<p class="text-sm text-destructive">{error}</p>
	{/if}

	<Card>
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
</div>
