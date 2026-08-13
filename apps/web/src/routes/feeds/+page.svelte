<script lang="ts">
	import { onMount } from 'svelte';
	import type { Feed, Folder } from '@lumia/core';
	import { lumia } from '$lib/client';
	import { requireAuth } from '$lib/require-auth';

	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let loading = $state(true);
	let importing = $state(false);
	let error = $state<string | null>(null);
	let newFolderName = $state('');

	function folderName(folderId: string | null): string {
		if (!folderId) return 'Sans dossier';
		return folders.find((folder) => folder.id === folderId)?.name ?? 'Sans dossier';
	}

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

<h1>Mes flux</h1>

<section>
	<h2>Importer depuis Feedly</h2>
	<p>Exporte tes flux en OPML depuis Feedly, puis importe le fichier ici.</p>
	<input
		type="file"
		accept=".opml,.xml,text/xml"
		disabled={importing}
		onchange={importOpml}
	/>
	{#if importing}<p>Import en cours…</p>{/if}
</section>

<section>
	<h2>Nouveau dossier</h2>
	<form onsubmit={createFolder}>
		<input type="text" bind:value={newFolderName} placeholder="Nom du dossier" />
		<button type="submit">Créer</button>
	</form>
</section>

{#if error}
	<p class="error">{error}</p>
{/if}

{#if loading}
	<p>Chargement…</p>
{:else if feeds.length === 0}
	<p>Aucun flux pour le moment.</p>
{:else}
	<table>
		<thead>
			<tr>
				<th>Titre</th>
				<th>Dossier</th>
				<th>URL</th>
				<th></th>
			</tr>
		</thead>
		<tbody>
			{#each feeds as feed (feed.id)}
				<tr>
					<td>{feed.title}</td>
					<td>{folderName(feed.folder_id)}</td>
					<td><a href={feed.url} target="_blank" rel="noopener">{feed.url}</a></td>
					<td><button onclick={() => removeFeed(feed.id)}>Supprimer</button></td>
				</tr>
			{/each}
		</tbody>
	</table>
{/if}

<style>
	section {
		margin-bottom: 1.5rem;
	}
	form {
		display: flex;
		gap: 0.5rem;
	}
	table {
		width: 100%;
		border-collapse: collapse;
	}
	th,
	td {
		text-align: left;
		padding: 0.4rem;
		border-bottom: 1px solid #eee;
	}
	.error {
		color: #c0392b;
	}
</style>
