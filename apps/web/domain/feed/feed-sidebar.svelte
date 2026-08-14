<script lang="ts">
	import { base } from '$app/paths';
	import type { Feed, Folder, UnreadCounts } from '@lumia/core';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import FolderIcon from '@lucide/svelte/icons/folder';
	import Rss from '@lucide/svelte/icons/rss';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import Star from '@lucide/svelte/icons/star';
	import ListMusic from '@lucide/svelte/icons/list-music';
	import { AnimatedList } from '@lumia/ui';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		folders: Folder[];
		feeds: Feed[];
		unread?: UnreadCounts;
		selectedFolderId: string;
		selectedFeedId: string;
		onSelectAll: () => void;
		onSelectFolder: (folderId: string) => void;
		onSelectFeed: (feedId: string) => void;
		onMarkFeedRead?: (feedId: string) => void;
		onMarkFolderRead?: (folderId: string) => void;
	}

	let {
		folders,
		feeds,
		unread = { total: 0, feeds: {}, folders: {} },
		selectedFolderId,
		selectedFeedId,
		onSelectAll,
		onSelectFolder,
		onSelectFeed,
		onMarkFeedRead,
		onMarkFolderRead
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
		{t('feeds.sidebarLabel')}
		{#if unread.total > 0}
			<span class="rounded-full bg-primary px-1.5 text-[11px] font-semibold text-primary-foreground">
				{unread.total}
			</span>
		{/if}
	</span>
	<ChevronDown class="size-4 transition-transform {mobileOpen ? '' : '-rotate-90'}" />
</button>

<aside
	id="feed-nav"
	aria-label={t('feeds.sidebarLabel')}
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
		<span class="flex-1 text-left">{t('feeds.allArticles')}</span>
		{#if unread.total > 0}
			<span class="text-xs font-semibold">{unread.total}</span>
		{/if}
	</button>

	<div class="mt-4 flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto">
		{#each folders as folder (folder.id)}
			{@const isFolderActive = selectedFolderId === folder.id}
			{@const folderUnread = unread.folders[folder.id] ?? 0}
			<div>
				<div class="group/folder flex items-center">
					<button
						onclick={() => onSelectFolder(folder.id)}
						aria-current={isFolderActive ? 'true' : undefined}
						class="flex flex-1 items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm font-medium transition-colors {isFolderActive
							? 'bg-primary text-primary-foreground'
							: 'text-zinc-300 hover:bg-white/10 hover:text-white'}"
					>
						<FolderIcon class="size-4" />
						<span class="flex-1 truncate text-left">{folder.name}</span>
						{#if folderUnread > 0}
							<span class="text-xs font-semibold">{folderUnread}</span>
						{/if}
					</button>
					{#if onMarkFolderRead && folderUnread > 0}
						<button
							onclick={() => onMarkFolderRead(folder.id)}
							aria-label={t('feeds.markAllReadIn', { name: folder.name })}
							title={t('feeds.markAllRead')}
							class="rounded-md p-1 text-zinc-400 opacity-0 transition-opacity hover:text-white focus-visible:opacity-100 group-hover/folder:opacity-100"
						>
							<CheckCheck class="size-3.5" />
						</button>
					{/if}
					<button
						onclick={() => toggle(folder.id)}
						aria-expanded={!collapsed[folder.id]}
						aria-label={collapsed[folder.id]
							? t('feeds.expand', { name: folder.name })
							: t('feeds.collapse', { name: folder.name })}
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
							{@const feedUnread = unread.feeds[feed.id] ?? 0}
							<div class="group/feed flex items-center">
								<button
									onclick={() => onSelectFeed(feed.id)}
									aria-current={selectedFeedId === feed.id ? 'true' : undefined}
									class="flex flex-1 items-center gap-2 truncate rounded-md px-2 py-1 text-left text-sm transition-colors {selectedFeedId ===
									feed.id
										? 'font-medium text-white'
										: 'text-zinc-300 hover:text-white'}"
								>
									<Rss class="size-3.5 shrink-0" />
									<span class="flex-1 truncate">{feed.title}</span>
									{#if feedUnread > 0}
										<span class="text-xs font-semibold">{feedUnread}</span>
									{/if}
								</button>
								{#if onMarkFeedRead && feedUnread > 0}
									<button
										onclick={() => onMarkFeedRead(feed.id)}
										aria-label={t('feeds.markAllReadIn', { name: feed.title })}
										title={t('feeds.markAllRead')}
										class="rounded-md p-1 text-zinc-400 opacity-0 transition-opacity hover:text-white focus-visible:opacity-100 group-hover/feed:opacity-100"
									>
										<CheckCheck class="size-3.5" />
									</button>
								{/if}
							</div>
						{/snippet}
					</AnimatedList>
				{/if}
			</div>
		{/each}

		{#if unfiledFeeds.length > 0}
			<span class="mt-2 px-2.5 text-xs font-medium uppercase tracking-wide text-zinc-400">
				{t('feeds.noFolder')}
			</span>
			<AnimatedList items={unfiledFeeds} getKey={(feed) => feed.id}>
				{#snippet children(feed)}
					{@const feedUnread = unread.feeds[feed.id] ?? 0}
					<button
						onclick={() => onSelectFeed(feed.id)}
						aria-current={selectedFeedId === feed.id ? 'true' : undefined}
						class="flex w-full items-center gap-2 truncate rounded-md px-2.5 py-1 text-left text-sm transition-colors {selectedFeedId ===
						feed.id
							? 'font-medium text-white'
							: 'text-zinc-400 hover:text-white'}"
					>
						<Rss class="size-3.5 shrink-0" />
						<span class="flex-1 truncate">{feed.title}</span>
						{#if feedUnread > 0}
							<span class="text-xs font-semibold">{feedUnread}</span>
						{/if}
					</button>
				{/snippet}
			</AnimatedList>
		{/if}
	</div>

	<a
		href="{base}/playlists"
		class="mt-auto flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-zinc-400 transition-colors hover:bg-white/10 hover:text-white"
	>
		<ListMusic class="size-4" />
		{t('nav.playlists')}
	</a>
	<a
		href="{base}/favoris"
		class="flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm font-medium text-zinc-400 transition-colors hover:bg-white/10 hover:text-white"
	>
		<Star class="size-4" />
		{t('nav.favorites')}
	</a>
</aside>
