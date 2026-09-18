<script lang="ts">
	import { onMount } from 'svelte';
	import type { SavedSearch } from '@lumia/core';
	import { Button, Card, CardContent, Input, toast } from '@lumia/ui';
	import Bell from '@lucide/svelte/icons/bell';
	import BellOff from '@lucide/svelte/icons/bell-off';
	import X from '@lucide/svelte/icons/x';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let savedSearches = $state<SavedSearch[]>([]);
	let name = $state('');
	let query = $state('');
	let saving = $state(false);
	let error = $state<string | null>(null);

	async function load() {
		try {
			savedSearches = await lumia.savedSearch.listSavedSearches();
		} catch {
			error = t('savedSearches.loadFailed');
		}
	}

	async function add(event: SubmitEvent) {
		event.preventDefault();
		const trimmedName = name.trim();
		if (trimmedName.length === 0) {
			error = t('savedSearches.nameRequired');
			return;
		}
		saving = true;
		error = null;
		try {
			const trimmedQuery = query.trim();
			const created = await lumia.savedSearch.createSavedSearch(trimmedName, {
				query: trimmedQuery.length > 0 ? trimmedQuery : undefined
			});
			savedSearches = [...savedSearches, created];
			name = '';
			query = '';
			toast(t('savedSearches.saveDone'));
		} catch {
			error = t('savedSearches.saveFailed');
		} finally {
			saving = false;
		}
	}

	async function toggleAlert(savedSearch: SavedSearch) {
		try {
			const updated = await lumia.savedSearch.updateSavedSearch(savedSearch.id, {
				isAlert: !savedSearch.is_alert
			});
			savedSearches = savedSearches.map((item) => (item.id === updated.id ? updated : item));
			toast(updated.is_alert ? t('savedSearches.alertOn') : t('savedSearches.alertOff'));
		} catch {
			toast(t('savedSearches.saveFailed'), { tone: 'destructive' });
		}
	}

	async function remove(savedSearch: SavedSearch) {
		try {
			await lumia.savedSearch.deleteSavedSearch(savedSearch.id);
			savedSearches = savedSearches.filter((item) => item.id !== savedSearch.id);
		} catch {
			toast(t('savedSearches.deleteFailed'), { tone: 'destructive' });
		}
	}

	onMount(load);
</script>

<Card>
	<CardContent class="flex flex-col gap-4 pt-6">
		<div>
			<h2 class="text-sm font-semibold text-muted-foreground">{t('savedSearches.title')}</h2>
			<p class="mt-1 text-xs text-muted-foreground">{t('savedSearches.intro')}</p>
		</div>

		<form class="flex flex-wrap items-end gap-2" onsubmit={add}>
			<label class="flex flex-1 flex-col gap-1 text-sm">
				<span class="font-medium">{t('savedSearches.name')}</span>
				<Input bind:value={name} placeholder={t('savedSearches.namePlaceholder')} maxlength={100} />
			</label>
			<label class="flex flex-1 flex-col gap-1 text-sm">
				<span class="font-medium">{t('savedSearches.query')}</span>
				<Input bind:value={query} placeholder={t('savedSearches.queryPlaceholder')} maxlength={200} />
			</label>
			<Button data-test-saved-search-submit type="submit" disabled={saving}
				>{saving ? t('common.adding') : t('common.add')}</Button
			>
		</form>

		{#if error}
			<p data-test-saved-searches-error role="alert" class="text-sm text-destructive">{error}</p>
		{/if}

		{#if savedSearches.length === 0}
			<p data-test-saved-searches-empty class="text-xs text-muted-foreground">{t('common.none')}</p>
		{:else}
			<ul class="flex flex-col gap-2">
				{#each savedSearches as savedSearch (savedSearch.id)}
					<li
						data-test-saved-search={savedSearch.id}
						class="flex items-center gap-2 rounded-md border border-border px-3 py-2"
					>
						<div class="flex-1">
							<p class="text-sm font-medium">{savedSearch.name}</p>
							<p class="text-xs text-muted-foreground">
								{savedSearch.unread_count === 1
									? t('savedSearches.unreadCountOne')
									: t('savedSearches.unreadCount', { count: savedSearch.unread_count })}
							</p>
						</div>
						<button
							data-test-saved-search-alert-toggle={savedSearch.id}
							type="button"
							onclick={() => toggleAlert(savedSearch)}
							class="flex min-h-8 min-w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary"
							aria-pressed={savedSearch.is_alert}
							title={savedSearch.is_alert
								? t('savedSearches.alertEnabled')
								: t('savedSearches.alertDisabled')}
						>
							{#if savedSearch.is_alert}
								<Bell class="size-4" />
							{:else}
								<BellOff class="size-4" />
							{/if}
							<span class="sr-only">
								{savedSearch.is_alert
									? t('savedSearches.alertEnabled')
									: t('savedSearches.alertDisabled')}
							</span>
						</button>
						<button
							data-test-saved-search-remove={savedSearch.id}
							type="button"
							onclick={() => remove(savedSearch)}
							class="flex min-h-8 min-w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary"
						>
							<X class="size-4" />
							<span class="sr-only">{t('savedSearches.removeOne', { name: savedSearch.name })}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</CardContent>
</Card>
