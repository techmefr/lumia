<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { Highlight } from '@lumia/core';
	import { Skeleton, toast } from '@lumia/ui';
	import Highlighter from '@lucide/svelte/icons/highlighter';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import HighlightCard from '$domain/highlight/highlight-card.svelte';

	let highlights = $state<Highlight[]>([]);
	let loading = $state(true);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);

	async function load() {
		try {
			highlights = await lumia.highlight.listHighlights();
		} catch {
			error = 'highlights.loadFailed';
		} finally {
			loading = false;
		}
	}

	async function saveNote(highlightId: string, note: string | null): Promise<boolean> {
		try {
			const updated = await lumia.highlight.updateHighlightNote(highlightId, note);
			highlights = highlights.map((item) => (item.id === highlightId ? updated : item));
			return true;
		} catch {
			toast(t('highlights.noteFailed'));
			return false;
		}
	}

	async function remove(highlightId: string) {
		try {
			await lumia.highlight.deleteHighlight(highlightId);
			highlights = highlights.filter((item) => item.id !== highlightId);
			toast(t('highlights.removed'));
		} catch {
			toast(t('highlights.removeFailed'));
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-6">
	<div>
		<h1 class="flex items-center gap-2 text-2xl font-semibold">
			<Highlighter class="size-6 text-primary" />
			{t('highlights.title')}
		</h1>
		<p class="text-sm text-muted-foreground">{t('highlights.intro')}</p>
	</div>

	{#if loading}
		<div role="status" aria-label={t('common.loading')} class="flex flex-col gap-3">
			{#each Array(3)}
				<Skeleton class="h-20 w-full" />
			{/each}
		</div>
	{:else if error}
		<p role="alert" class="text-sm text-destructive">{t(error)}</p>
	{:else if highlights.length === 0}
		<p data-test-highlights-empty class="text-sm text-muted-foreground">
			{t('highlights.empty')}
		</p>
		<a href="{base}/articles" class="w-fit text-sm text-primary hover:underline">
			{t('nav.articles')}
		</a>
	{:else}
		<ul class="flex flex-col gap-3">
			{#each highlights as highlight (highlight.id)}
				<HighlightCard
					{highlight}
					showArticle
					onsavenote={(note) => saveNote(highlight.id, note)}
					ondelete={() => remove(highlight.id)}
				/>
			{/each}
		</ul>
	{/if}
</div>
