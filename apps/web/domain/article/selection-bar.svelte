<script lang="ts">
	import type { PlaylistSummary } from '@lumia/core';
	import { Button } from '@lumia/ui';
	import CheckCheck from '@lucide/svelte/icons/check-check';
	import Circle from '@lucide/svelte/icons/circle';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import BookmarkX from '@lucide/svelte/icons/bookmark-x';
	import Star from '@lucide/svelte/icons/star';
	import StarOff from '@lucide/svelte/icons/star-off';
	import ListPlus from '@lucide/svelte/icons/list-plus';
	import X from '@lucide/svelte/icons/x';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		count: number;
		/** How many articles are loaded, which is the ceiling "select all" can reach. */
		loadedCount: number;
		playlists: PlaylistSummary[];
		busy?: boolean;
		onMarkRead: () => void;
		onMarkUnread: () => void;
		onSave: () => void;
		onUnsave: () => void;
		onFavorite: () => void;
		onUnfavorite: () => void;
		onAddToPlaylist: (playlistId: string) => void;
		onSelectAll: () => void;
		onClose: () => void;
	}

	let {
		count,
		loadedCount,
		playlists,
		busy = false,
		onMarkRead,
		onMarkUnread,
		onSave,
		onUnsave,
		onFavorite,
		onUnfavorite,
		onAddToPlaylist,
		onSelectAll,
		onClose
	}: Props = $props();

	let playlistId = $state('');

	const empty = $derived(count === 0);
	const disabled = $derived(empty || busy);

	function addToPlaylist() {
		if (!playlistId) return;
		onAddToPlaylist(playlistId);
	}
</script>

<!-- Stays in the flow above the grid rather than floating over it: an overlay covers the cards the
	 reader is deciding about, and on a phone it lands on top of the first row. -->
<section
	data-test-selection-bar
	class="flex flex-col gap-3 rounded-2xl border border-primary/40 bg-card p-3 sm:flex-row sm:items-center sm:justify-between"
	aria-label={t('selection.barLabel')}
>
	<div class="flex items-center gap-3">
		<p data-test-selection-count class="text-sm font-medium" role="status" aria-live="polite">
			{empty ? t('selection.none') : t('selection.count', { count })}
		</p>
		<Button
			data-test-selection-all
			variant="ghost"
			size="sm"
			onclick={onSelectAll}
			disabled={loadedCount === 0}
		>
			{t('selection.selectAll', { count: loadedCount })}
		</Button>
	</div>

	<div class="flex flex-wrap items-center gap-2" role="group" aria-label={t('selection.actions')}>
		<Button data-test-selection-read variant="outline" size="sm" {disabled} onclick={onMarkRead}>
			<CheckCheck class="size-4" />
			{t('selection.markRead')}
		</Button>
		<Button
			data-test-selection-unread
			variant="outline"
			size="sm"
			{disabled}
			onclick={onMarkUnread}
		>
			<Circle class="size-4" />
			{t('selection.markUnread')}
		</Button>
		<Button data-test-selection-save variant="outline" size="sm" {disabled} onclick={onSave}>
			<Bookmark class="size-4" />
			{t('selection.save')}
		</Button>
		<Button data-test-selection-unsave variant="outline" size="sm" {disabled} onclick={onUnsave}>
			<BookmarkX class="size-4" />
			{t('selection.unsave')}
		</Button>
		<Button
			data-test-selection-favorite
			variant="outline"
			size="sm"
			{disabled}
			onclick={onFavorite}
		>
			<Star class="size-4" />
			{t('selection.favorite')}
		</Button>
		<Button
			data-test-selection-unfavorite
			variant="outline"
			size="sm"
			{disabled}
			onclick={onUnfavorite}
		>
			<StarOff class="size-4" />
			{t('selection.unfavorite')}
		</Button>

		{#if playlists.length > 0}
			<label class="sr-only" for="selection-playlist">{t('selection.playlistLabel')}</label>
			<select
				id="selection-playlist"
				data-test-selection-playlist
				bind:value={playlistId}
				{disabled}
				class="min-h-9 rounded-md border bg-background px-2 text-sm"
			>
				<option value="">{t('selection.playlistPlaceholder')}</option>
				{#each playlists as playlist (playlist.id)}
					<option value={playlist.id}>{playlist.name}</option>
				{/each}
			</select>
			<Button
				data-test-selection-playlist-add
				variant="outline"
				size="sm"
				disabled={disabled || !playlistId}
				onclick={addToPlaylist}
			>
				<ListPlus class="size-4" />
				{t('selection.addToPlaylist')}
			</Button>
		{/if}

		<Button data-test-selection-close variant="ghost" size="sm" onclick={onClose}>
			<X class="size-4" />
			{t('selection.close')}
		</Button>
	</div>
</section>
