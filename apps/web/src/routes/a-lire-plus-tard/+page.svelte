<script lang="ts">
	import { onMount } from 'svelte';
	import type { ArticleSummary } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, toast } from '@lumia/ui';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import Plus from '@lucide/svelte/icons/plus';
	import { lumia } from '$technical/api/client';
	import { requireAuth } from '$technical/auth/require-auth';
	import ArticleGrid from '$domain/article/article-grid.svelte';

	const PAGE_SIZE = 24;

	let articles = $state<ArticleSummary[]>([]);
	let loading = $state(true);
	let loadingMore = $state(false);
	let hasMore = $state(false);
	let error = $state<string | null>(null);
	let newUrl = $state('');
	let savingUrl = $state(false);
	let saveError = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			const loaded = await lumia.recommendation.getSaved(PAGE_SIZE, 0);
			articles = loaded;
			hasMore = loaded.length === PAGE_SIZE;
		} catch {
			error = 'Impossible de charger ta liste de lecture.';
		} finally {
			loading = false;
		}
	}

	async function loadMore() {
		if (loadingMore || !hasMore) return;
		loadingMore = true;
		try {
			const next = await lumia.recommendation.getSaved(PAGE_SIZE, articles.length);
			articles = [...articles, ...next];
			hasMore = next.length === PAGE_SIZE;
		} catch {
			error = 'Impossible de charger la suite.';
		} finally {
			loadingMore = false;
		}
	}

	async function saveUrl(event: SubmitEvent) {
		event.preventDefault();
		const url = newUrl.trim();
		if (!url) return;

		savingUrl = true;
		saveError = null;
		try {
			const saved = await lumia.article.saveUrl(url);
			newUrl = '';
			await load();
			toast(`« ${saved.title} » enregistré.`);
		} catch {
			saveError =
				'Impossible d’enregistrer cette page — elle est peut-être inaccessible ou sans contenu lisible.';
		} finally {
			savingUrl = false;
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Bookmark class="size-6 text-primary" />
			À lire plus tard
		</h1>
		<p class="text-sm text-muted-foreground">
			Les articles enregistrés depuis leur page, et les pages ajoutées par URL.
		</p>
	</div>

	<Card>
		<CardHeader>
			<CardTitle>Enregistrer une page</CardTitle>
			<CardDescription>
				Colle l'URL de n'importe quelle page : Lumia en extrait le texte et l'ajoute ici.
			</CardDescription>
		</CardHeader>
		<CardContent>
			{#if saveError}
				<p role="alert" class="mb-2 text-sm text-destructive">{saveError}</p>
			{/if}
			<form class="flex flex-wrap items-end gap-2" onsubmit={saveUrl}>
				<div class="flex max-w-sm flex-1 flex-col gap-1.5">
					<Label for="save-url">URL de la page</Label>
					<Input
						id="save-url"
						type="url"
						bind:value={newUrl}
						placeholder="https://exemple.com/un-article"
						required
						disabled={savingUrl}
					/>
				</div>
				<Button type="submit" disabled={savingUrl}>
					<Plus class="size-4" />
					{savingUrl ? 'Extraction…' : 'Enregistrer'}
				</Button>
			</form>
		</CardContent>
	</Card>

	{#if error}
		<p role="alert" class="text-sm text-destructive">{error}</p>
	{/if}

	<ArticleGrid {articles} {loading}>
		{#snippet empty()}
			<div class="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6">
				<p class="text-sm text-muted-foreground">
					Rien pour le moment — enregistre un article depuis sa page, ou colle une URL ci-dessus.
				</p>
				<Button size="sm" href="/articles">Parcourir les articles</Button>
			</div>
		{/snippet}

		{#snippet footer()}
			{#if hasMore}
				<div class="mt-6 flex justify-center">
					<Button variant="outline" onclick={loadMore} disabled={loadingMore}>
						{loadingMore ? 'Chargement…' : 'Charger plus'}
					</Button>
				</div>
			{/if}
		{/snippet}
	</ArticleGrid>
</div>
