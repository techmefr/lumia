<script lang="ts">
	import { onMount } from 'svelte';
	import type { InstanceFeed } from '@lumia/core';
	import { Button, Card, CardContent, Skeleton, toast } from '@lumia/ui';
	import Library from '@lucide/svelte/icons/library';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		/** Called after feeds were attached so the caller can refresh its own lists. */
		onAttached: () => void | Promise<void>;
	}

	let { onAttached }: Props = $props();

	let candidates = $state<InstanceFeed[]>([]);
	let selected = $state<string[]>([]);
	let loading = $state(true);
	let attaching = $state(false);
	let failed = $state(false);

	const allSelected = $derived(candidates.length > 0 && selected.length === candidates.length);

	async function load() {
		loading = true;
		failed = false;
		try {
			candidates = await lumia.feed.listInstanceFeeds();
			selected = [];
		} catch {
			failed = true;
		} finally {
			loading = false;
		}
	}

	function toggle(externalFeedId: string) {
		selected = selected.includes(externalFeedId)
			? selected.filter((id) => id !== externalFeedId)
			: [...selected, externalFeedId];
	}

	function toggleAll() {
		selected = allSelected ? [] : candidates.map((candidate) => candidate.external_feed_id);
	}

	async function attach() {
		if (selected.length === 0) return;
		attaching = true;
		try {
			const attached = await lumia.feed.attachInstanceFeeds(selected);
			// Dropped from the list rather than refetched: the backend answers with exactly what it
			// created, and a reload would ask the instance for the same list one round trip later.
			const taken = new Set(attached.map((feed) => feed.external_feed_id));
			candidates = candidates.filter(
				(candidate) => !taken.has(candidate.external_feed_id)
			);
			selected = [];
			toast(t('instanceFeeds.attachedToast', { count: attached.length }));
			await onAttached();
		} catch {
			toast(t('instanceFeeds.attachFailed'), { tone: 'destructive' });
		} finally {
			attaching = false;
		}
	}

	onMount(load);
</script>

<Card>
	<CardContent class="flex flex-col gap-4 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
				<Library class="size-4" />
				{t('instanceFeeds.title')}
			</h2>
			<p class="mt-1 text-xs text-muted-foreground">{t('instanceFeeds.intro')}</p>
		</div>

		{#if failed}
			<p data-test-instance-error role="alert" class="text-sm text-destructive">
				{t('instanceFeeds.loadFailed')}
			</p>
		{/if}

		{#if loading}
			<div
				data-test-instance-loading
				role="status"
				aria-label={t('instanceFeeds.loading')}
				class="flex flex-col gap-2"
			>
				{#each Array(3)}
					<Skeleton class="h-10 w-full rounded-xl" />
				{/each}
			</div>
		{:else if candidates.length === 0}
			<p data-test-instance-empty class="text-sm text-muted-foreground">
				{t('instanceFeeds.empty')}
			</p>
		{:else}
			<label class="flex items-center gap-2 text-sm font-medium">
				<input
					data-test-instance-select-all
					type="checkbox"
					checked={allSelected}
					onchange={toggleAll}
					class="size-4"
				/>
				{t('instanceFeeds.selectAll')}
			</label>

			<ul class="flex flex-col gap-1">
				{#each candidates as candidate (candidate.external_feed_id)}
					<li data-test-instance-feed={candidate.external_feed_id}>
						<label class="flex items-start gap-3 rounded-xl border p-3">
							<input
								data-test-instance-checkbox
								type="checkbox"
								checked={selected.includes(candidate.external_feed_id)}
								onchange={() => toggle(candidate.external_feed_id)}
								class="mt-1 size-4"
							/>
							<span class="min-w-0 flex-1">
								<span data-test-instance-title class="block font-medium">{candidate.title}</span>
								<span class="block truncate text-xs text-muted-foreground">{candidate.url}</span>
							</span>
							<span
								data-test-instance-category
								class="shrink-0 rounded-full bg-secondary px-2 py-0.5 text-[11px] text-secondary-foreground"
							>
								{candidate.category ?? t('instanceFeeds.noCategory')}
							</span>
						</label>
					</li>
				{/each}
			</ul>

			<div>
				<Button
					data-test-instance-attach
					onclick={attach}
					disabled={attaching || selected.length === 0}
				>
					{attaching
						? t('common.adding')
						: t('instanceFeeds.attach', { count: selected.length })}
				</Button>
			</div>
		{/if}
	</CardContent>
</Card>
