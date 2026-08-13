<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary, Feed, Folder } from '@lumia/core';
	import { lumia } from '$lib/client';
	import { requireAuth } from '$lib/require-auth';

	let articles = $state<ArticleSummary[]>([]);
	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let selectedFolderId = $state('');
	let selectedFeedId = $state('');
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadArticles() {
		loading = true;
		error = null;
		try {
			articles = await lumia.article.listArticles({
				folderId: selectedFolderId || undefined,
				feedId: selectedFeedId || undefined
			});
		} catch {
			error = 'Impossible de charger les articles.';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		if (!requireAuth()) return;
		void Promise.all([lumia.feed.listFolders(), lumia.feed.listFeeds()]).then(([f, fe]) => {
			folders = f;
			feeds = fe;
		});
		void loadArticles();
	});
</script>

<h1>Articles</h1>

<div class="filters">
	<label>
		Dossier
		<select bind:value={selectedFolderId} onchange={loadArticles}>
			<option value="">Tous</option>
			{#each folders as folder (folder.id)}
				<option value={folder.id}>{folder.name}</option>
			{/each}
		</select>
	</label>
	<label>
		Flux
		<select bind:value={selectedFeedId} onchange={loadArticles}>
			<option value="">Tous</option>
			{#each feeds as feed (feed.id)}
				<option value={feed.id}>{feed.title}</option>
			{/each}
		</select>
	</label>
</div>

{#if error}
	<p class="error">{error}</p>
{/if}

{#if loading}
	<p>Chargement…</p>
{:else if articles.length === 0}
	<p>Aucun article. Importe ou ajoute des flux depuis <a href="/feeds">Mes flux</a>.</p>
{:else}
	<ul>
		{#each articles as article (article.id)}
			<li>
				<a href="/articles/{article.id}">{article.title}</a>
				{#if article.summary}<p>{article.summary}</p>{/if}
			</li>
		{/each}
	</ul>
{/if}

<style>
	.filters {
		display: flex;
		gap: 1rem;
		margin-bottom: 1rem;
	}
	ul {
		list-style: none;
		padding: 0;
	}
	li {
		padding: 0.75rem 0;
		border-bottom: 1px solid #eee;
	}
	.error {
		color: #c0392b;
	}
</style>
