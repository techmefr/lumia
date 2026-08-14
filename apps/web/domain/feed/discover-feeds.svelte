<script lang="ts">
	import { onMount } from 'svelte';
	import type { DiscoverSuggestion, Folder } from '@lumia/core';
	import { Button, Card, CardContent, Skeleton, toast } from '@lumia/ui';
	import Compass from '@lucide/svelte/icons/compass';
	import Plus from '@lucide/svelte/icons/plus';
	import ExternalLink from '@lucide/svelte/icons/external-link';
	import RefreshCw from '@lucide/svelte/icons/refresh-cw';
	import { lumia } from '$technical/api/client';

	interface Props {
		folders: Folder[];
		/** Called after a successful subscription so the caller can refresh its own lists. */
		onSubscribed: () => void | Promise<void>;
	}

	let { folders, onSubscribed }: Props = $props();

	let suggestions = $state<DiscoverSuggestion[]>([]);
	let loading = $state(true);
	let adding = $state<string | null>(null);
	let folderId = $state('');
	let error = $state<string | null>(null);

	async function load() {
		loading = true;
		error = null;
		try {
			suggestions = await lumia.feed.discoverFeeds();
		} catch {
			error = 'Impossible de charger les suggestions.';
		} finally {
			loading = false;
		}
	}

	async function subscribe(suggestion: DiscoverSuggestion) {
		adding = suggestion.url;
		try {
			await lumia.feed.addFeedByUrl(suggestion.url, folderId || null);
			// Drop it from the list right away rather than refetching: the backend excludes what is
			// already subscribed, so a reload would do the same thing one round-trip later.
			suggestions = suggestions.filter((item) => item.url !== suggestion.url);
			toast(`${suggestion.title} ajouté.`);
			await onSubscribed();
		} catch {
			toast(`${suggestion.title} est injoignable.`, { tone: 'destructive' });
		} finally {
			adding = null;
		}
	}

	onMount(load);
</script>

<Card>
	<CardContent class="flex flex-col gap-4 pt-6">
		<div class="flex flex-wrap items-start justify-between gap-2">
			<div>
				<h2 class="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
					<Compass class="size-4" />
					Découvrir des sources
				</h2>
				<p class="mt-1 text-xs text-muted-foreground">
					Un catalogue livré avec Lumia, classé selon les sujets que tu lis. Rien n'est déduit des
					abonnements des autres comptes de l'instance.
				</p>
			</div>
			<Button variant="ghost" size="sm" onclick={load}>
				<RefreshCw class="size-4" />
				Actualiser
			</Button>
		</div>

		{#if folders.length > 0}
			<label class="flex flex-col gap-1 text-sm sm:max-w-xs">
				<span class="font-medium">Ranger dans</span>
				<select
					bind:value={folderId}
					class="min-h-9 rounded-md border border-input bg-background px-3 text-sm"
				>
					<option value="">Sans dossier</option>
					{#each folders as folder (folder.id)}
						<option value={folder.id}>{folder.name}</option>
					{/each}
				</select>
			</label>
		{/if}

		{#if error}
			<p role="alert" class="text-sm text-destructive">{error}</p>
		{/if}

		{#if loading}
			<div role="status" aria-label="Chargement des suggestions" class="flex flex-col gap-2">
				{#each Array(3)}
					<Skeleton class="h-20 w-full rounded-xl" />
				{/each}
			</div>
		{:else if suggestions.length === 0}
			<p class="text-sm text-muted-foreground">
				Tu es déjà abonné à tout le catalogue. Ajoute une URL à la main pour aller plus loin.
			</p>
		{:else}
			<ul class="flex flex-col gap-2">
				{#each suggestions as suggestion (suggestion.url)}
					<li class="flex flex-wrap items-start gap-3 rounded-xl border p-3">
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center gap-2">
								<span class="font-medium">{suggestion.title}</span>
								<span
									class="rounded-full bg-secondary px-2 py-0.5 text-[11px] uppercase text-secondary-foreground"
								>
									{suggestion.language}
								</span>
								{#if suggestion.affinity !== null}
									<span class="text-xs text-primary" title="Proximité avec ce que tu lis">
										affinité {suggestion.affinity}
									</span>
								{/if}
							</div>
							<p class="mt-0.5 text-sm text-muted-foreground">{suggestion.description}</p>
							<p class="mt-1 flex flex-wrap gap-1 text-[11px] text-muted-foreground">
								{#each suggestion.topics as topic (topic)}
									<span class="rounded bg-muted px-1.5 py-0.5">{topic}</span>
								{/each}
							</p>
						</div>
						<div class="flex shrink-0 items-center gap-1">
							<Button
								size="sm"
								onclick={() => subscribe(suggestion)}
								disabled={adding === suggestion.url}
							>
								<Plus class="size-4" />
								{adding === suggestion.url ? 'Ajout…' : "S'abonner"}
							</Button>
							<Button variant="ghost" size="sm" href={suggestion.site_url} target="_blank">
								<ExternalLink class="size-4" />
								<span class="sr-only">Voir {suggestion.title}</span>
							</Button>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</CardContent>
</Card>
