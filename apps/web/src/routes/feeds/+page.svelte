<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import type { Feed, Folder } from '@lumia/core';
	import {
		Badge,
		Button,
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
		Input,
		Label,
		MagicBento,
		Separator
	} from '@lumia/ui';
	import Upload from '@lucide/svelte/icons/upload';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import FolderPlus from '@lucide/svelte/icons/folder-plus';
	import Plus from '@lucide/svelte/icons/plus';
	import Rss from '@lucide/svelte/icons/rss';
	import Inbox from '@lucide/svelte/icons/inbox';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Shuffle from '@lucide/svelte/icons/shuffle';
	import Pencil from '@lucide/svelte/icons/pencil';
	import { toast } from '@lumia/ui';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';
	import { resolveFolderName } from '$domain/feed/resolve-folder-name';
	import FeedSidebar from '$domain/feed/feed-sidebar.svelte';
	import DiscoverFeeds from '$domain/feed/discover-feeds.svelte';

	let folders = $state<Folder[]>([]);
	let feeds = $state<Feed[]>([]);
	let loading = $state(true);
	let importing = $state(false);
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
	let newFolderName = $state('');
	let selectedFolderId = $state('');
	let selectedFeedId = $state('');
	let newFeedUrl = $state('');
	let newFeedFolderId = $state('');
	let addingFeed = $state(false);
	let addFeedError = $state<MessageKey | null>(null);
	let renamingFolderId = $state<string | null>(null);
	let folderRenameValue = $state('');
	let renamingFeedId = $state<string | null>(null);
	let feedRenameValue = $state('');

	const selectedFolder = $derived(folders.find((f) => f.id === selectedFolderId) ?? null);
	const selectedFeed = $derived(feeds.find((f) => f.id === selectedFeedId) ?? null);
	const feedsInSelectedFolder = $derived(
		selectedFolderId ? feeds.filter((feed) => feed.folder_id === selectedFolderId) : []
	);

	async function load() {
		loading = true;
		error = null;
		try {
			[folders, feeds] = await Promise.all([lumia.feed.listFolders(), lumia.feed.listFeeds()]);
		} catch {
			error = 'feeds.loadFailed';
		} finally {
			loading = false;
		}
	}

	async function createFolder(event: SubmitEvent) {
		event.preventDefault();
		if (!newFolderName.trim()) return;
		await lumia.feed.createFolder(newFolderName.trim());
		newFolderName = '';
		await load();
	}

	async function addFeed(event: SubmitEvent) {
		event.preventDefault();
		if (!newFeedUrl.trim()) return;

		addingFeed = true;
		addFeedError = null;
		try {
			await lumia.feed.addFeedByUrl(newFeedUrl.trim(), newFeedFolderId || null);
			newFeedUrl = '';
			newFeedFolderId = '';
			await load();
		} catch {
			addFeedError = 'feeds.addFailed';
		} finally {
			addingFeed = false;
		}
	}

	async function removeFeed(feedId: string) {
		const feed = feeds.find((candidate) => candidate.id === feedId);
		await lumia.feed.deleteFeed(feedId);
		if (selectedFeedId === feedId) selectedFeedId = '';
		await load();
		toast(t('feeds.removedToast', { title: feed?.title ?? t('feeds.fallbackTitle') }), {
			action:
				feed && feed.source_type === 'miniflux'
					? {
							label: t('feeds.restore'),
							run: async () => {
								await lumia.feed.addFeedByUrl(feed.url, feed.folder_id);
								await load();
							}
						}
					: undefined
		});
	}

	async function renameFolder(event: SubmitEvent) {
		event.preventDefault();
		const name = folderRenameValue.trim();
		if (!renamingFolderId || !name) return;
		try {
			await lumia.feed.renameFolder(renamingFolderId, name);
			renamingFolderId = null;
			await load();
		} catch {
			toast(t('feeds.renameFolderFailed'), { tone: 'destructive' });
		}
	}

	async function removeFolder(folder: Folder) {
		try {
			await lumia.feed.deleteFolder(folder.id);
			if (selectedFolderId === folder.id) selectedFolderId = '';
			await load();
			// Deleting a folder never deletes its feeds, so the undo only has to recreate the folder
			// and refile what used to be in it.
			const previousFeedIds = feeds
				.filter((feed) => feed.folder_id === folder.id)
				.map((feed) => feed.id);
			toast(t('feeds.folderDeletedToast', { name: folder.name }), {
				action: {
					label: t('common.undo'),
					run: async () => {
						const recreated = await lumia.feed.createFolder(folder.name);
						for (const feedId of previousFeedIds) {
							await lumia.feed.updateFeed(feedId, { folder_id: recreated.id });
						}
						await load();
					}
				}
			});
		} catch {
			toast(t('feeds.deleteFolderFailed'), { tone: 'destructive' });
		}
	}

	async function moveFeed(feedId: string, folderId: string) {
		try {
			await lumia.feed.updateFeed(feedId, { folder_id: folderId || null });
			await load();
			toast(t('feeds.movedToast'));
		} catch {
			toast(t('feeds.moveFailed'), { tone: 'destructive' });
		}
	}

	async function retitleFeed(event: SubmitEvent) {
		event.preventDefault();
		const title = feedRenameValue.trim();
		if (!renamingFeedId || !title) return;
		try {
			await lumia.feed.updateFeed(renamingFeedId, { title });
			renamingFeedId = null;
			await load();
		} catch {
			toast(t('feeds.renameFeedFailed'), { tone: 'destructive' });
		}
	}

	async function importOpml(event: Event) {
		const input = event.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		importing = true;
		error = null;
		try {
			await lumia.feed.importOpml(file);
			await load();
		} catch {
			error = 'feeds.importFailed';
		} finally {
			importing = false;
			input.value = '';
		}
	}

	function selectAll() {
		selectedFolderId = '';
		selectedFeedId = '';
	}

	function selectFolder(folderId: string) {
		selectedFolderId = selectedFolderId === folderId ? '' : folderId;
		selectedFeedId = '';
	}

	function selectFeed(feedId: string) {
		selectedFeedId = selectedFeedId === feedId ? '' : feedId;
		selectedFolderId = '';
	}

	function viewArticles() {
		if (selectedFeedId) void goto(`${base}/articles?feed_id=${selectedFeedId}`);
		else if (selectedFolderId) void goto(`${base}/articles?folder_id=${selectedFolderId}`);
	}

	function readInSwipeMode() {
		if (selectedFeedId) {
			const label = encodeURIComponent(selectedFeed?.title ?? '');
			void goto(`${base}/lire?feed_id=${selectedFeedId}&label=${label}`);
		} else if (selectedFolderId) {
			const label = encodeURIComponent(selectedFolder?.name ?? '');
			void goto(`${base}/lire?folder_id=${selectedFolderId}&label=${label}`);
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<div class="flex flex-col gap-4 sm:flex-row sm:gap-6">
	<FeedSidebar
		{folders}
		{feeds}
		{selectedFolderId}
		{selectedFeedId}
		onSelectAll={selectAll}
		onSelectFolder={selectFolder}
		onSelectFeed={selectFeed}
	/>

	<div class="flex min-w-0 flex-1 flex-col gap-6">
		<h1 class="text-2xl font-semibold">{t('feeds.title')}</h1>

		{#if error}
			<p role="alert" class="text-sm text-destructive">{t(error)}</p>
		{/if}

		<DiscoverFeeds {folders} onSubscribed={load} />

		{#if selectedFeed}
			<Card>
				<CardHeader>
					<CardTitle class="flex items-center gap-2">
						<Rss class="size-4 text-primary" />
						{selectedFeed.title}
					</CardTitle>
					<CardDescription>
						<a href={selectedFeed.url} target="_blank" rel="noopener noreferrer" class="hover:underline">
							{selectedFeed.url}
						</a>
					</CardDescription>
				</CardHeader>
				<CardContent class="flex flex-col gap-4">
					<div class="flex flex-wrap items-center gap-2">
						<Button onclick={viewArticles}>
							<Newspaper class="size-4" />
							{t('feeds.viewArticles')}
						</Button>
						<Button variant="secondary" onclick={readInSwipeMode}>
							<Shuffle class="size-4" />
							{t('feeds.swipeMode')}
						</Button>
						<Button variant="ghost" onclick={() => removeFeed(selectedFeed!.id)}>
							<Trash2 class="size-4" />
							{t('feeds.removeFeed')}
						</Button>
					</div>

					<Separator />

					<div class="flex flex-wrap items-end gap-4">
						{#if renamingFeedId === selectedFeed.id}
							<form class="flex items-end gap-2" onsubmit={retitleFeed}>
								<div class="flex flex-col gap-1.5">
									<Label for="feed-title">{t('feeds.feedName')}</Label>
									<Input id="feed-title" bind:value={feedRenameValue} required />
								</div>
								<Button type="submit" size="sm">{t('common.rename')}</Button>
								<Button
									type="button"
									size="sm"
									variant="ghost"
									onclick={() => (renamingFeedId = null)}
								>
									{t('common.cancel')}
								</Button>
							</form>
						{:else}
							<Button
								size="sm"
								variant="outline"
								onclick={() => {
									renamingFeedId = selectedFeed!.id;
									feedRenameValue = selectedFeed!.title;
								}}
							>
								<Pencil class="size-4" />
								{t('common.rename')}
							</Button>
						{/if}

						<div class="flex flex-col gap-1.5">
							<Label for="feed-folder">{t('feeds.folder')}</Label>
							<select
								id="feed-folder"
								value={selectedFeed.folder_id ?? ''}
								onchange={(event) => moveFeed(selectedFeed!.id, event.currentTarget.value)}
								class="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
							>
								<option value="">{t('feeds.noFolder')}</option>
								{#each folders as folder (folder.id)}
									<option value={folder.id}>{folder.name}</option>
								{/each}
							</select>
						</div>
					</div>
				</CardContent>
			</Card>
		{:else if selectedFolder}
			<Card>
				<CardHeader>
					<CardTitle>{selectedFolder.name}</CardTitle>
					<CardDescription>
						{t('feeds.countInFolder', { count: feedsInSelectedFolder.length })}
					</CardDescription>
				</CardHeader>
				<CardContent class="flex flex-col gap-4">
					<div class="flex flex-wrap items-center gap-2">
						<Button onclick={viewArticles}>
							<Newspaper class="size-4" />
							{t('feeds.viewFolderArticles')}
						</Button>
						<Button variant="secondary" onclick={readInSwipeMode}>
							<Shuffle class="size-4" />
							{t('feeds.swipeMode')}
						</Button>
					</div>

					<Separator />

					{#if renamingFolderId === selectedFolder.id}
						<form class="flex items-end gap-2" onsubmit={renameFolder}>
							<div class="flex max-w-xs flex-1 flex-col gap-1.5">
								<Label for="folder-name">{t('feeds.folderName')}</Label>
								<Input id="folder-name" bind:value={folderRenameValue} required />
							</div>
							<Button type="submit" size="sm">{t('common.rename')}</Button>
							<Button
								type="button"
								size="sm"
								variant="ghost"
								onclick={() => (renamingFolderId = null)}
							>
								{t('common.cancel')}
							</Button>
						</form>
					{:else}
						<div class="flex flex-wrap items-center gap-2">
							<Button
								size="sm"
								variant="outline"
								onclick={() => {
									renamingFolderId = selectedFolder!.id;
									folderRenameValue = selectedFolder!.name;
								}}
							>
								<Pencil class="size-4" />
								{t('feeds.renameFolder')}
							</Button>
							<Button size="sm" variant="ghost" onclick={() => removeFolder(selectedFolder!)}>
								<Trash2 class="size-4" />
								{t('feeds.deleteFolder')}
							</Button>
							<span class="text-xs text-muted-foreground">{t('feeds.folderFeedsKept')}</span>
						</div>
					{/if}
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<CardTitle>{t('feeds.folderFeeds')}</CardTitle>
				</CardHeader>
				<CardContent>
					{#if feedsInSelectedFolder.length === 0}
						<p class="flex items-center gap-2 text-sm text-muted-foreground">
							<Inbox class="size-4" />
							{t('feeds.folderEmpty')}
						</p>
					{:else}
						<div class="flex flex-col">
							{#each feedsInSelectedFolder as feed, index (feed.id)}
								{#if index > 0}<Separator />{/if}
								<button
									onclick={() => selectFeed(feed.id)}
									class="flex items-center justify-between gap-4 py-3 text-left"
								>
									<div class="flex items-center gap-3">
										<Rss class="size-4 shrink-0 text-primary" />
										<span class="font-medium">{feed.title}</span>
									</div>
								</button>
							{/each}
						</div>
					{/if}
				</CardContent>
			</Card>
		{:else}
			<MagicBento class="grid-cols-1 sm:grid-cols-2">
				<Card class="magic-bento-cell sm:col-span-2">
					<CardHeader>
						<CardTitle>{t('feeds.addTitle')}</CardTitle>
						<CardDescription>{t('feeds.addDescription')}</CardDescription>
					</CardHeader>
					<CardContent>
						{#if addFeedError}
							<p role="alert" class="mb-2 text-sm text-destructive">{t(addFeedError)}</p>
						{/if}
						<form class="flex flex-wrap items-end gap-2" onsubmit={addFeed}>
							<div class="flex max-w-sm flex-1 flex-col gap-1.5">
								<Label for="new-feed-url">{t('feeds.urlLabel')}</Label>
								<Input
									id="new-feed-url"
									type="url"
									bind:value={newFeedUrl}
									placeholder={t('feeds.urlPlaceholder')}
									required
									disabled={addingFeed}
								/>
							</div>
							<div class="flex flex-col gap-1.5">
								<Label for="new-feed-folder">{t('feeds.folder')}</Label>
								<select
									id="new-feed-folder"
									bind:value={newFeedFolderId}
									disabled={addingFeed}
									class="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
								>
									<option value="">{t('feeds.noFolder')}</option>
									{#each folders as folder (folder.id)}
										<option value={folder.id}>{folder.name}</option>
									{/each}
								</select>
							</div>
							<Button type="submit" disabled={addingFeed}>
								<Plus class="size-4" />
								{addingFeed ? t('common.adding') : t('common.add')}
							</Button>
						</form>
					</CardContent>
				</Card>

				<Card class="magic-bento-cell">
					<CardHeader>
						<CardTitle>{t('feeds.importTitle')}</CardTitle>
						<CardDescription>{t('feeds.importDescription')}</CardDescription>
					</CardHeader>
					<CardContent>
						<label
							class="flex w-fit cursor-pointer items-center gap-2 rounded-md border border-dashed border-input px-4 py-2 text-sm hover:bg-accent"
						>
							<Upload class="size-4" />
							{importing ? t('feeds.importing') : t('feeds.importChoose')}
							<input
								type="file"
								accept=".opml,.xml,text/xml"
								disabled={importing}
								onchange={importOpml}
								class="hidden"
							/>
						</label>
					</CardContent>
				</Card>

				<Card class="magic-bento-cell">
					<CardHeader>
						<CardTitle>{t('feeds.newFolder')}</CardTitle>
					</CardHeader>
					<CardContent>
						<form class="flex items-end gap-2" onsubmit={createFolder}>
							<div class="flex max-w-xs flex-1 flex-col gap-1.5">
								<Label for="new-folder-name">{t('feeds.folderName')}</Label>
								<Input id="new-folder-name" type="text" bind:value={newFolderName} required />
							</div>
							<Button type="submit" variant="secondary">
								<FolderPlus class="size-4" />
								{t('feeds.create')}
							</Button>
						</form>
					</CardContent>
				</Card>

				<Card class="magic-bento-cell sm:col-span-2">
					<CardHeader>
						<CardTitle>{t('feeds.subscribed')}</CardTitle>
					</CardHeader>
					<CardContent>
						{#if loading}
							<p role="status" class="text-sm text-muted-foreground">{t('common.loading')}</p>
						{:else if feeds.length === 0}
							<p class="flex items-center gap-2 text-sm text-muted-foreground">
								<Inbox class="size-4" />
								{t('feeds.empty')}
							</p>
						{:else}
							<div class="flex flex-col">
								{#each feeds as feed, index (feed.id)}
									{#if index > 0}<Separator />{/if}
									<div
										class="flex animate-in items-center justify-between gap-4 py-3 fade-in slide-in-from-left-1 duration-300"
										style={`animation-delay: ${index * 40}ms`}
									>
										<div class="flex items-center gap-3">
											<Rss class="size-4 shrink-0 text-primary" />
											<div class="flex flex-col gap-1">
												<span class="font-medium">{feed.title}</span>
												<a href={feed.url} target="_blank" rel="noopener noreferrer" class="text-xs text-muted-foreground hover:underline">
													{feed.url}
												</a>
											</div>
										</div>
										<div class="flex items-center gap-3">
											<Badge variant="secondary">
											{resolveFolderName(folders, feed.folder_id, t('feeds.noFolder'))}
										</Badge>
											<Button variant="ghost" size="icon" onclick={() => removeFeed(feed.id)}>
												<Trash2 class="size-4" />
											</Button>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</CardContent>
				</Card>
			</MagicBento>
		{/if}
	</div>
</div>
