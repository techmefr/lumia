<script lang="ts">
	import { onMount } from 'svelte';
	import type { LumiaClient } from '@lumia/core';
	import { Button } from '@lumia/ui';
	import type { ExtensionApi } from '$technical/browser/extension-api';
	import { openLumiaClient } from '$technical/api/lumia-session';
	import { t } from '$technical/i18n/i18n';
	import { OUTCOME_MESSAGE } from '$domain/save/save-feedback';
	import ArticleList from '$domain/reader/article-list.svelte';
	import ArticleReader from '$domain/reader/article-reader.svelte';
	import { readerSession, type ReaderSession } from '$domain/reader/reader-session';

	let { extension }: { extension: ExtensionApi } = $props();

	const ARTICLE_HASH = '#article/';

	let client = $state<LumiaClient | null>(null);
	let session = $state<ReaderSession | null>(null);
	let hash = $state(window.location.hash);

	const articleId = $derived(hash.startsWith(ARTICLE_HASH) ? hash.slice(ARTICLE_HASH.length) : null);

	onMount(async () => {
		client = await openLumiaClient(extension.storage.local);
		session = readerSession(client);
	});
</script>

<svelte:window onhashchange={() => (hash = window.location.hash)} />

<main class="flex flex-col gap-4 p-3">
	<h1 class="font-serif text-lg">{t('reader.title')}</h1>
	{#if session === 'ready' && client}
		{#if articleId}
			<ArticleReader {client} {articleId} onsessionlost={() => (session = 'unauthenticated')} />
		{:else}
			<ArticleList {client} onsessionlost={() => (session = 'unauthenticated')} />
		{/if}
	{:else if session !== null}
		<div class="flex flex-col items-start gap-3">
			<p data-test-session-message role="alert" class="text-sm text-muted-foreground">
				{t(OUTCOME_MESSAGE[session === 'unconfigured' ? 'unconfigured' : 'unauthenticated'])}
			</p>
			<Button data-test-open-settings onclick={() => extension.runtime.openOptionsPage()}>
				{t('popup.openSettings')}
			</Button>
		</div>
	{/if}
</main>
