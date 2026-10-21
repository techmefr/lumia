<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, type Tag } from '@lumia/core';
	import { Button, Card, CardContent, Input, toast } from '@lumia/ui';
	import Pencil from '@lucide/svelte/icons/pencil';
	import Trash2 from '@lucide/svelte/icons/trash-2';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let tags = $state<Tag[]>([]);
	let loaded = $state(false);
	let error = $state<string | null>(null);
	let editingId = $state<string | null>(null);
	let draft = $state('');

	async function load() {
		try {
			tags = await lumia.tag.listTags();
		} catch {
			error = t('tags.loadFailed');
		} finally {
			loaded = true;
		}
	}

	function startRename(tag: Tag) {
		editingId = tag.id;
		draft = tag.name;
		error = null;
	}

	function cancelRename() {
		editingId = null;
		error = null;
	}

	async function rename(event: SubmitEvent, tag: Tag) {
		event.preventDefault();
		const name = draft.trim();
		if (!name) return;
		try {
			const renamed = await lumia.tag.renameTag(tag.id, name);
			tags = tags.map((item) => (item.id === tag.id ? renamed : item));
			editingId = null;
			error = null;
			toast(t('tags.renamed'));
		} catch (failure) {
			error =
				failure instanceof ApiError && failure.status === 409
					? t('tags.nameTaken')
					: t('tags.saveFailed');
		}
	}

	async function remove(tag: Tag) {
		if (!confirm(t('tags.deleteConfirm', { name: tag.name, count: tag.article_count }))) return;
		try {
			await lumia.tag.deleteTag(tag.id);
			tags = tags.filter((item) => item.id !== tag.id);
			toast(t('tags.deleted'));
		} catch {
			toast(t('tags.saveFailed'), { tone: 'destructive' });
		}
	}

	onMount(load);
</script>

<Card>
	<CardContent class="flex flex-col gap-4 pt-6">
		<div>
			<h2 class="text-sm font-semibold text-muted-foreground">{t('tags.title')}</h2>
			<p class="mt-1 text-xs text-muted-foreground">{t('tags.manageIntro')}</p>
		</div>

		{#if error}
			<p data-test-tags-error role="alert" class="text-sm text-destructive">{error}</p>
		{/if}

		{#if loaded && tags.length === 0 && !error}
			<p data-test-tags-empty class="text-sm text-muted-foreground">{t('tags.empty')}</p>
		{/if}

		<ul class="flex flex-col gap-2">
			{#each tags as tag (tag.id)}
				<li data-test-tag-row={tag.id} class="flex flex-wrap items-center gap-2">
					{#if editingId === tag.id}
						<form class="flex flex-1 items-center gap-2" onsubmit={(event) => rename(event, tag)}>
							<label class="flex-1">
								<span class="sr-only">{t('tags.rename', { name: tag.name })}</span>
								<Input data-test-tag-rename-input bind:value={draft} maxlength={40} />
							</label>
							<Button data-test-tag-rename-save type="submit">{t('common.save')}</Button>
							<Button
								data-test-tag-rename-cancel
								type="button"
								variant="outline"
								onclick={cancelRename}>{t('common.cancel')}</Button
							>
						</form>
					{:else}
						<span data-test-tag-name class="flex-1 text-sm font-medium">{tag.name}</span>
						<span data-test-tag-count class="text-xs text-muted-foreground">
							{t('tags.count', { count: tag.article_count })}
						</span>
						<button
							data-test-tag-rename
							type="button"
							onclick={() => startRename(tag)}
							class="flex min-h-8 min-w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground"
						>
							<Pencil class="size-4" aria-hidden="true" />
							<span class="sr-only">{t('tags.rename', { name: tag.name })}</span>
						</button>
						<button
							data-test-tag-delete
							type="button"
							onclick={() => remove(tag)}
							class="flex min-h-8 min-w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-destructive"
						>
							<Trash2 class="size-4" aria-hidden="true" />
							<span class="sr-only">{t('tags.delete', { name: tag.name })}</span>
						</button>
					{/if}
				</li>
			{/each}
		</ul>
	</CardContent>
</Card>
