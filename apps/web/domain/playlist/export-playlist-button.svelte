<script lang="ts">
	import { ApiError } from '@lumia/core';
	import { toast, Icon } from '@lumia/ui';
	import { BookDownloadIcon, Loading03Icon } from '@hugeicons/core-free-icons';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		playlistId: string;
		name: string;
		/** How long to wait between two looks at the job; the worker needs seconds, not frames. */
		pollMs?: number;
		/** Looks before giving up, so a job lost by the worker does not keep a tab polling forever. */
		maxPolls?: number;
	}

	const { playlistId, name, pollMs = 1500, maxPolls = 200 }: Props = $props();

	let pending = $state(false);

	function messageFor(error: unknown) {
		if (error instanceof ApiError && error.status === 422) return t('playlist.exportBookEmpty');
		if (error instanceof ApiError && error.status === 413) return t('playlist.exportBookTooLarge');
		return t('playlist.exportBookFailed');
	}

	function fileName(value: string) {
		const stem = value
			.replace(/[\\/:*?"<>|]+/g, ' ')
			.replace(/\s+/g, ' ')
			.trim();
		return `${stem || 'playlist'}.epub`;
	}

	async function untilFinished(jobId: string) {
		for (let poll = 0; poll < maxPolls; poll += 1) {
			const job = await lumia.playlist.getExport(jobId);
			if (job.status === 'ready') return;
			if (job.status === 'failed') throw new Error('export failed');
			await new Promise((resolve) => setTimeout(resolve, pollMs));
		}
		throw new Error('export timed out');
	}

	async function exportBook() {
		pending = true;
		try {
			const job = await lumia.playlist.exportPlaylistEpub(playlistId);
			await untilFinished(job.id);
			const blob = await lumia.playlist.downloadExport(job.id);
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = fileName(name);
			link.click();
			URL.revokeObjectURL(url);
		} catch (error) {
			toast(messageFor(error));
		} finally {
			pending = false;
		}
	}
</script>

<button
	type="button"
	onclick={exportBook}
	disabled={pending}
	aria-busy={pending}
	data-test-export-playlist-button
	class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
>
	{#if pending}
		<Icon icon={Loading03Icon} class="size-4 animate-spin" />
		{t('playlist.exportingBook')}
	{:else}
		<Icon icon={BookDownloadIcon} class="size-4" />
		{t('playlist.exportBook')}
	{/if}
</button>
