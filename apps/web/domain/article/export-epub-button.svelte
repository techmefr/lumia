<script lang="ts">
	import { toast, Icon } from '@lumia/ui';
	import { BookDownloadIcon, Loading03Icon } from '@hugeicons/core-free-icons';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articleId: string;
		title: string;
	}

	const { articleId, title }: Props = $props();

	let pending = $state(false);

	function fileName(value: string) {
		const stem = value
			.replace(/[\\/:*?"<>|]+/g, ' ')
			.replace(/\s+/g, ' ')
			.trim();
		return `${stem || 'article'}.epub`;
	}

	async function exportEpub() {
		pending = true;
		try {
			const blob = await lumia.article.exportArticleEpub(articleId);
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = fileName(title);
			link.click();
			URL.revokeObjectURL(url);
		} catch {
			toast(t('article.exportEpubFailed'));
		} finally {
			pending = false;
		}
	}
</script>

<button
	type="button"
	onclick={exportEpub}
	disabled={pending}
	aria-busy={pending}
	data-test-export-epub-button
	class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
>
	{#if pending}
		<Icon icon={Loading03Icon} class="size-4 animate-spin" />
		{t('article.exportingEpub')}
	{:else}
		<Icon icon={BookDownloadIcon} class="size-4" />
		{t('article.exportEpub')}
	{/if}
</button>
