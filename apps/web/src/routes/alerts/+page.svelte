<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import type { AlertNotification, SavedSearch } from '@lumia/core';
	import { ApiError } from '@lumia/core';
	import { Button, Card, CardContent, Input, toast } from '@lumia/ui';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { requireAuth } from '$technical/auth/require-auth';

	let searches = $state<SavedSearch[]>([]);
	let notifications = $state<AlertNotification[]>([]);
	let unreadNotifications = $state(0);
	let name = $state('');
	let query = $state('');
	let alert = $state(true);
	let saving = $state(false);
	let error = $state<MessageKey | null>(null);

	function searchHref(search: SavedSearch): string {
		const params = new URLSearchParams({ q: search.query });
		if (search.feed_id) params.set('feed_id', search.feed_id);
		if (search.folder_id) params.set('folder_id', search.folder_id);
		return `${base}/articles?${params}`;
	}

	async function load() {
		try {
			const [loadedSearches, loadedNotifications] = await Promise.all([
				lumia.savedSearch.listSavedSearches(),
				lumia.savedSearch.listNotifications()
			]);
			searches = loadedSearches;
			notifications = loadedNotifications.items;
			unreadNotifications = loadedNotifications.unread_count;
		} catch {
			error = 'alerts.loadFailed';
		}
	}

	async function create(event: SubmitEvent) {
		event.preventDefault();
		if (query.trim().length < 2) {
			error = 'alerts.tooShort';
			return;
		}
		saving = true;
		error = null;
		try {
			await lumia.savedSearch.createSavedSearch({
				name: name.trim() || query.trim(),
				query: query.trim(),
				alert
			});
			name = '';
			query = '';
			toast(t('alerts.created'));
			await load();
		} catch (failure) {
			error =
				failure instanceof ApiError && failure.status === 409
					? 'alerts.nameTaken'
					: 'alerts.saveFailed';
		} finally {
			saving = false;
		}
	}

	async function toggleAlert(search: SavedSearch) {
		try {
			await lumia.savedSearch.updateSavedSearch(search.id, { alert: !search.alert });
			await load();
		} catch {
			toast(t('alerts.actionFailed'), { tone: 'destructive' });
		}
	}

	async function remove(search: SavedSearch) {
		try {
			await lumia.savedSearch.deleteSavedSearch(search.id);
			await load();
		} catch {
			toast(t('alerts.actionFailed'), { tone: 'destructive' });
		}
	}

	async function markAllRead() {
		try {
			await lumia.savedSearch.markNotificationsRead();
			await load();
		} catch {
			toast(t('alerts.actionFailed'), { tone: 'destructive' });
		}
	}

	onMount(() => {
		if (requireAuth()) void load();
	});
</script>

<svelte:head>
	<title>{t('alerts.title')}</title>
</svelte:head>

<h1 class="mb-4 font-serif text-2xl font-semibold">{t('alerts.title')}</h1>

<div class="flex flex-col gap-6">
	<Card>
		<CardContent class="flex flex-col gap-4 pt-6">
			<p class="text-sm text-muted-foreground">{t('alerts.intro')}</p>
			<form class="flex flex-wrap items-end gap-2" onsubmit={create}>
				<label class="flex flex-col gap-1 text-sm">
					<span class="font-medium">{t('alerts.name')}</span>
					<Input data-test-search-name bind:value={name} maxlength={80} />
				</label>
				<label class="flex flex-1 flex-col gap-1 text-sm">
					<span class="font-medium">{t('alerts.query')}</span>
					<Input data-test-search-query bind:value={query} maxlength={200} />
				</label>
				<label class="flex min-h-9 items-center gap-2 text-sm">
					<input data-test-search-alert type="checkbox" bind:checked={alert} />
					{t('alerts.notify')}
				</label>
				<Button data-test-search-submit type="submit" disabled={saving}>{t('alerts.create')}</Button>
			</form>
			{#if error}
				<p data-test-alerts-error role="alert" class="text-sm text-destructive">{t(error)}</p>
			{/if}
		</CardContent>
	</Card>

	{#if searches.length === 0}
		<p data-test-searches-empty class="text-sm text-muted-foreground">{t('alerts.empty')}</p>
	{:else}
		<ul class="flex flex-col gap-2">
			{#each searches as search (search.id)}
				<li data-test-search={search.id} class="flex flex-wrap items-center gap-3 rounded-md border p-3">
					<a data-test-search-link href={searchHref(search)} class="font-medium underline-offset-2 hover:underline">
						{search.name}
					</a>
					<span class="text-xs text-muted-foreground">{search.query}</span>
					<span data-test-search-unread class="text-xs">{t('alerts.unread', { count: search.unread_count })}</span>
					<label class="ml-auto flex min-h-9 items-center gap-2 text-sm">
						<input
							data-test-search-toggle
							type="checkbox"
							checked={search.alert}
							onchange={() => toggleAlert(search)}
						/>
						{t('alerts.toggle', { name: search.name })}
					</label>
					<button
						data-test-search-remove
						type="button"
						class="flex min-h-9 min-w-9 items-center justify-center rounded-md hover:bg-secondary"
						onclick={() => remove(search)}
					>
						<Trash2 class="size-4" />
						<span class="sr-only">{t('alerts.remove', { name: search.name })}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}

	<section aria-labelledby="notifications-title" class="flex flex-col gap-2">
		<div class="flex items-center gap-3">
			<h2 id="notifications-title" class="text-lg font-semibold">{t('alerts.notifications')}</h2>
			{#if unreadNotifications > 0}
				<Button data-test-mark-all-read variant="ghost" size="sm" onclick={markAllRead}>
					{t('alerts.markAllRead')}
				</Button>
			{/if}
		</div>
		{#if notifications.length === 0}
			<p data-test-notifications-empty class="text-sm text-muted-foreground">{t('alerts.noNotifications')}</p>
		{:else}
			<ul class="flex flex-col gap-1">
				{#each notifications as notification (notification.id)}
					<li data-test-notification={notification.id} data-test-notification-read={notification.read}>
						<a
							href="{base}/articles/{notification.article_id}"
							class="block rounded-md p-2 hover:bg-secondary {notification.read ? '' : 'font-semibold'}"
						>
							{notification.article_title}
							<span class="block text-xs font-normal text-muted-foreground">
								{t('alerts.matchedBy', { search: notification.saved_search_name })}
							</span>
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
</div>
