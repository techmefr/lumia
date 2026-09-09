<script lang="ts">
	import type { Folder, UnreadCounts } from '@lumia/core';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		folders: Folder[];
		unread: UnreadCounts;
		selectedFolderId: string;
		onSelectAll: () => void;
		onSelectFolder: (folderId: string) => void;
	}

	let { folders, unread, selectedFolderId, onSelectAll, onSelectFolder }: Props = $props();

	function chipClass(active: boolean): string {
		return active
			? 'border-primary bg-primary text-primary-foreground'
			: 'border-border bg-card text-foreground hover:border-muted-foreground';
	}
</script>

<!-- The sidebar is hidden on a phone, so the sections need a reachable form of their own. A single
	 scrolling row keeps the whole set one thumb-swipe away instead of behind a menu. -->
<div
	class="-mx-4 overflow-x-auto px-4 sm:mx-0 sm:px-0"
	role="group"
	aria-label={t('sections.group')}
>
	<div class="flex w-max items-center gap-2 pb-1">
		<button
			data-test-section-chip=""
			type="button"
			onclick={onSelectAll}
			aria-pressed={selectedFolderId === ''}
			class="flex min-h-9 items-center gap-1.5 whitespace-nowrap rounded-full border px-3.5 text-sm font-medium transition-colors {chipClass(
				selectedFolderId === ''
			)}"
		>
			{t('sections.all')}
			{#if unread.total > 0}
				<span data-test-chip-count class="text-xs opacity-70">{unread.total}</span>
			{/if}
		</button>
		{#each folders as folder (folder.id)}
			{@const count = unread.folders[folder.id] ?? 0}
			<button
				data-test-section-chip={folder.id}
				type="button"
				onclick={() => onSelectFolder(folder.id)}
				aria-pressed={selectedFolderId === folder.id}
				class="flex min-h-9 items-center gap-1.5 whitespace-nowrap rounded-full border px-3.5 text-sm font-medium transition-colors {chipClass(
					selectedFolderId === folder.id
				)}"
			>
				{folder.name}
				{#if count > 0}
					<span data-test-chip-count class="text-xs opacity-70">{count}</span>
				{/if}
			</button>
		{/each}
	</div>
</div>
