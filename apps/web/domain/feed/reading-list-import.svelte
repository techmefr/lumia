<script lang="ts">
	import { onDestroy } from 'svelte';
	import type { ReadingListImportProgress, ReadingListSource } from '@lumia/core';
	import { ApiError } from '@lumia/core';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle, Label, Icon } from '@lumia/ui';
	import { Upload01Icon } from '@hugeicons/core-free-icons';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';

	const POLL_INTERVAL_MS = 2000;
	const SOURCES: { value: ReadingListSource; label: MessageKey; accept: string }[] = [
		{ value: 'pocket', label: 'feeds.readingImportPocket', accept: '.html,text/html' },
		{ value: 'wallabag', label: 'feeds.readingImportWallabag', accept: '.json,application/json' },
		{ value: 'instapaper', label: 'feeds.readingImportInstapaper', accept: '.csv,text/csv' }
	];

	let source = $state<ReadingListSource>('pocket');
	let starting = $state(false);
	let progress = $state<ReadingListImportProgress | null>(null);
	let error = $state<MessageKey | null>(null);
	let pollTimer: ReturnType<typeof setTimeout> | undefined;
	let destroyed = false;

	const accept = $derived(SOURCES.find((choice) => choice.value === source)?.accept);
	const running = $derived(starting || (progress !== null && !progress.finished));

	async function poll(importId: string) {
		try {
			progress = await lumia.article.getReadingListImportProgress(importId);
		} catch {
			error = 'feeds.readingImportFailed';
			return;
		}
		if (destroyed) return;
		if (!progress.finished) {
			pollTimer = setTimeout(() => poll(importId), POLL_INTERVAL_MS);
		}
	}

	async function start(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		starting = true;
		error = null;
		progress = null;
		try {
			const started = await lumia.article.importReadingList(source, file);
			progress = { total: started.total, saved: 0, failed: 0, finished: started.total === 0 };
			if (!progress.finished) await poll(started.import_id);
		} catch (cause) {
			error =
				cause instanceof ApiError && cause.status === 413
					? 'feeds.readingImportTooLarge'
					: 'feeds.readingImportFailed';
		} finally {
			starting = false;
			input.value = '';
		}
	}

	onDestroy(() => {
		destroyed = true;
		clearTimeout(pollTimer);
	});
</script>

<Card class="magic-bento-cell" data-test-reading-import>
	<CardHeader>
		<CardTitle>{t('feeds.readingImportTitle')}</CardTitle>
		<CardDescription>{t('feeds.readingImportDescription')}</CardDescription>
	</CardHeader>
	<CardContent class="flex flex-col gap-3">
		<div class="flex flex-col gap-1.5 sm:max-w-xs">
			<Label for="reading-import-source">{t('feeds.readingImportSource')}</Label>
			<select
				id="reading-import-source"
				data-test-reading-import-source
				bind:value={source}
				disabled={running}
				class="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
			>
				{#each SOURCES as choice (choice.value)}
					<option value={choice.value}>{t(choice.label)}</option>
				{/each}
			</select>
		</div>
		<label
			class="flex w-fit cursor-pointer items-center gap-2 rounded-md border border-dashed border-input px-4 py-2 text-sm hover:bg-accent"
		>
			<Icon icon={Upload01Icon} class="size-4" />
			{t('feeds.readingImportChoose')}
			<input
				data-test-reading-import-input
				type="file"
				{accept}
				disabled={running}
				onchange={start}
				class="hidden"
			/>
		</label>
		{#if progress}
			<p data-test-reading-import-progress role="status" class="text-sm text-muted-foreground">
				{t(progress.finished ? 'feeds.readingImportDone' : 'feeds.readingImportProgress', {
					saved: progress.saved,
					failed: progress.failed,
					total: progress.total
				})}
			</p>
		{/if}
		{#if error}
			<p data-test-reading-import-error role="alert" class="text-sm text-destructive">
				{t(error)}
			</p>
		{/if}
	</CardContent>
</Card>
