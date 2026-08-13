<script lang="ts">
	import type { Feed, Folder } from '@lumia/core';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import FolderIcon from '@lucide/svelte/icons/folder';
	import Rss from '@lucide/svelte/icons/rss';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import Settings from '@lucide/svelte/icons/settings';
	import Star from '@lucide/svelte/icons/star';
	import { AnimatedList } from '@lumia/ui';

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

	let mobileOpen = $state(false);
</script>

<button
	onclick={() => (mobileOpen = !mobileOpen)}
	aria-expanded={mobileOpen}
	aria-controls="feed-nav"
	class="flex min-h-11 items-center justify-between gap-2 rounded-xl border bg-card px-3 py-2 text-sm font-medium shadow-sm sm:hidden"
>
	<span class="flex items-center gap-2">
		<FolderIcon class="size-4 text-primary" />
		Dossiers et flux
	</span>
	<ChevronDown class="size-4 transition-transform {mobileOpen ? '' : '-rotate-90'}" />
</button>

<aside
	id="feed-nav"
	aria-label="Dossiers et flux"
	class="{mobileOpen
		? 'flex'
		: 'hidden'} w-full shrink-0 flex-col gap-0.5 rounded-2xl border border-zinc-700 bg-zinc-900 p-3 text-zinc-300 shadow-xl dark:border-zinc-500 dark:bg-zinc-800 sm:sticky sm:top-[4.5rem] sm:flex sm:h-[calc(100vh-7.5rem)] sm:w-60"
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

	<div class="mt-4 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto">
		{#each folders as folder (folder.id)}
			{@const isFolderActive = selectedFolderId === folder.id}
			<div>
				<div class="flex items-center">
					<button
						onclick={() => onSelectFolder(folder.id)}
						aria-current={isFolderActive ? 'true' : undefined}
						class="flex flex-1 items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors {isFolderActive
							? 'bg-primary text-primary-foreground'
							: 'text-zinc-300 hover:bg-white/10 hover:text-white'}"
					>
						<FolderIcon class="size-4" />
						<span class="flex-1 truncate text-left">{folder.name}</span>
					</button>
					<button
						onclick={() => toggle(folder.id)}
						aria-expanded={!collapsed[folder.id]}
						aria-label="{collapsed[folder.id] ? 'Déplier' : 'Replier'} {folder.name}"
						class="rounded-md p-1 text-zinc-400 hover:text-white"
					>
						<ChevronDown
							class="size-3.5 transition-transform {collapsed[folder.id] ? '-rotate-90' : ''}"
						/>
					</button>
				</div>
				{#if !collapsed[folder.id]}
					<AnimatedList
						items={feedsForFolder(folder.id)}
						getKey={(feed) => feed.id}
						class="ml-4 border-l border-white/10 pl-2"
					>
						{#snippet children(feed)}
							<button
								onclick={() => onSelectFeed(feed.id)}
								aria-current={selectedFeedId === feed.id ? 'true' : undefined}
								class="flex items-center gap-2 truncate rounded-md px-2 py-1 text-left text-sm transition-colors {selectedFeedId ===
								feed.id
									? 'font-medium text-white'
									: 'text-zinc-300 hover:text-white'}"
							>
								<Rss class="size-3.5 shrink-0" />
								<span class="truncate">{feed.title}</span>
							</button>
						{/snippet}
					</AnimatedList>
				{/if}
			</div>
		{/each}

		{#if unfiledFeeds.length > 0}
			<span class="mt-2 px-2.5 text-xs font-medium uppercase tracking-wide text-zinc-400">
				Sans dossier
			</span>
			<AnimatedList items={unfiledFeeds} getKey={(feed) => feed.id}>
				{#snippet children(feed)}
					<button
						onclick={() => onSelectFeed(feed.id)}
						aria-current={selectedFeedId === feed.id ? 'true' : undefined}
						class="flex items-center gap-2 truncate rounded-md px-2.5 py-1 text-left text-sm transition-colors {selectedFeedId ===
						feed.id
							? 'font-medium text-white'
							: 'text-zinc-400 hover:text-white'}"
					>
						<Rss class="size-3.5 shrink-0" />
						<span class="truncate">{feed.title}</span>
					</button>
				{/snippet}
			</AnimatedList>
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
