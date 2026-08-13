<script lang="ts">
	import type { Feed, Folder } from '@lumia/core';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import FolderIcon from '@lucide/svelte/icons/folder';
	import Rss from '@lucide/svelte/icons/rss';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Settings from '@lucide/svelte/icons/settings';
	import Star from '@lucide/svelte/icons/star';

	interface Props {
		folders: Folder[];
		feeds: Feed[];
		selectedFolderId: string;
		selectedFeedId: string;
		onSelectAll: () => void;
		onSelectFolder: (folderId: string) => void;
		onSelectFeed: (feedId: string) => void;
	}

	let {
		folders,
		feeds,
		selectedFolderId,
		selectedFeedId,
		onSelectAll,
		onSelectFolder,
		onSelectFeed
	}: Props = $props();

	function feedsForFolder(folderId: string): Feed[] {
		return feeds.filter((feed) => feed.folder_id === folderId);
	}

	const unfiledFeeds = $derived(feeds.filter((feed) => feed.folder_id === null));
	let collapsed = $state<Record<string, boolean>>({});

	function toggle(folderId: string) {
		collapsed = { ...collapsed, [folderId]: !collapsed[folderId] };
	}

	const isAllActive = $derived(!selectedFolderId && !selectedFeedId);
</script>

<aside
	class="hidden w-60 shrink-0 flex-col gap-0.5 rounded-2xl bg-zinc-900 p-3 text-zinc-300 sm:flex dark:bg-zinc-950"
>
	<button
		onclick={onSelectAll}
		class="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors {isAllActive
			? 'bg-primary text-primary-foreground'
			: 'hover:bg-white/10 hover:text-white'}"
	>
		<Newspaper class="size-4" />
		Tous les articles
	</button>

	<div class="mt-4 flex flex-col gap-0.5">
		{#each folders as folder (folder.id)}
			{@const isFolderActive = selectedFolderId === folder.id}
			<div>
				<div class="flex items-center">
					<button
						onclick={() => onSelectFolder(folder.id)}
						class="flex flex-1 items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors {isFolderActive
							? 'bg-primary text-primary-foreground'
							: 'text-zinc-400 hover:bg-white/10 hover:text-white'}"
					>
						<FolderIcon class="size-4" />
						<span class="flex-1 truncate text-left">{folder.name}</span>
					</button>
					<button
						onclick={() => toggle(folder.id)}
						aria-label="Déplier {folder.name}"
						class="rounded-md p-1 text-zinc-500 hover:text-white"
					>
						<ChevronDown
							class="size-3.5 transition-transform {collapsed[folder.id] ? '-rotate-90' : ''}"
						/>
					</button>
				</div>
				{#if !collapsed[folder.id]}
					<div class="ml-4 flex flex-col gap-0.5 border-l border-white/10 pl-2">
						{#each feedsForFolder(folder.id) as feed (feed.id)}
							<button
								onclick={() => onSelectFeed(feed.id)}
								class="flex items-center gap-2 truncate rounded-md px-2 py-1 text-left text-sm transition-colors {selectedFeedId ===
								feed.id
									? 'font-medium text-white'
									: 'text-zinc-500 hover:text-white'}"
							>
								<Rss class="size-3.5 shrink-0" />
								<span class="truncate">{feed.title}</span>
							</button>
						{/each}
					</div>
				{/if}
			</div>
		{/each}

		{#if unfiledFeeds.length > 0}
			<span class="mt-2 px-2.5 text-xs font-medium uppercase tracking-wide text-zinc-500">
				Sans dossier
			</span>
			{#each unfiledFeeds as feed (feed.id)}
				<button
					onclick={() => onSelectFeed(feed.id)}
					class="flex items-center gap-2 truncate rounded-md px-2.5 py-1 text-left text-sm transition-colors {selectedFeedId ===
					feed.id
						? 'font-medium text-white'
						: 'text-zinc-500 hover:text-white'}"
				>
					<Rss class="size-3.5 shrink-0" />
					<span class="truncate">{feed.title}</span>
				</button>
			{/each}
		{/if}
	</div>

	<a
		href="/favoris"
		class="mt-auto flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-zinc-400 transition-colors hover:bg-white/10 hover:text-white"
	>
		<Star class="size-4" />
		Favoris
	</a>
	<a
		href="/settings"
		class="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-zinc-400 transition-colors hover:bg-white/10 hover:text-white"
	>
		<Settings class="size-4" />
		Réglages
	</a>
</aside>
