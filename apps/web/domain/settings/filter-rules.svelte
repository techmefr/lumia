<script lang="ts">
	import { onMount } from 'svelte';
	import type { FilterMode, FilterRule } from '@lumia/core';
	import { Button, Card, CardContent, Input, toast } from '@lumia/ui';
	import TrendingUp from '@lucide/svelte/icons/trending-up';
	import VolumeX from '@lucide/svelte/icons/volume-x';
	import X from '@lucide/svelte/icons/x';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let rules = $state<FilterRule[]>([]);
	let term = $state('');
	let mode = $state<FilterMode>('boost');
	let saving = $state(false);
	let error = $state<string | null>(null);

	const boosted = $derived(rules.filter((rule) => rule.mode === 'boost'));
	const muted = $derived(rules.filter((rule) => rule.mode === 'mute'));

	async function load() {
		try {
			rules = await lumia.recommendation.listFilterRules();
		} catch {
			error = t('rules.loadFailed');
		}
	}

	async function add(event: SubmitEvent) {
		event.preventDefault();
		const trimmed = term.trim();
		if (trimmed.length < 2) {
			error = t('rules.tooShort');
			return;
		}
		saving = true;
		error = null;
		try {
			const created = await lumia.recommendation.addFilterRule(trimmed, mode);
			// The backend is idempotent, so re-adding an existing rule returns it unchanged.
			if (!rules.some((rule) => rule.id === created.id)) rules = [...rules, created];
			term = '';
			toast(mode === 'boost' ? t('rules.boostDone') : t('rules.muteDone'));
		} catch {
			error = t('rules.saveFailed');
		} finally {
			saving = false;
		}
	}

	async function remove(rule: FilterRule) {
		try {
			await lumia.recommendation.deleteFilterRule(rule.id);
			rules = rules.filter((item) => item.id !== rule.id);
		} catch {
			toast(t('rules.deleteFailed'), { tone: 'destructive' });
		}
	}

	onMount(load);
</script>

<Card>
	<CardContent class="flex flex-col gap-4 pt-6">
		<div>
			<h2 class="text-sm font-semibold text-muted-foreground">{t('rules.title')}</h2>
			<p class="mt-1 text-xs text-muted-foreground">{t('rules.intro')}</p>
		</div>

		<form class="flex flex-wrap items-end gap-2" onsubmit={add}>
			<label class="flex flex-1 flex-col gap-1 text-sm">
				<span class="font-medium">{t('rules.term')}</span>
				<Input bind:value={term} placeholder={t('rules.termPlaceholder')} maxlength={80} />
			</label>
			<label class="flex flex-col gap-1 text-sm">
				<span class="font-medium">{t('rules.effect')}</span>
				<select
					bind:value={mode}
					class="min-h-9 rounded-md border border-input bg-background px-3 text-sm"
				>
					<option value="boost">{t('rules.boost')}</option>
					<option value="mute">{t('rules.mute')}</option>
				</select>
			</label>
			<Button type="submit" disabled={saving}>{saving ? t('common.adding') : t('common.add')}</Button>
		</form>

		{#if error}
			<p role="alert" class="text-sm text-destructive">{error}</p>
		{/if}

		<div class="flex flex-col gap-3">
			{#each [{ label: t('rules.boosted'), icon: TrendingUp, list: boosted }, { label: t('rules.muted'), icon: VolumeX, list: muted }] as group (group.label)}
				<div class="flex flex-col gap-1.5">
					<span class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
						<group.icon class="size-3.5" />
						{group.label}
					</span>
					{#if group.list.length === 0}
						<p class="text-xs text-muted-foreground">{t('common.none')}</p>
					{:else}
						<ul class="flex flex-wrap gap-1.5">
							{#each group.list as rule (rule.id)}
								<li>
									<button
										type="button"
										onclick={() => remove(rule)}
										class="flex min-h-8 items-center gap-1.5 rounded-full bg-secondary px-3 text-sm text-secondary-foreground transition-colors hover:bg-secondary/70"
									>
										{rule.term}
										<X class="size-3.5" />
										<span class="sr-only">{t('rules.removeOne', { term: rule.term })}</span>
									</button>
								</li>
							{/each}
						</ul>
					{/if}
				</div>
			{/each}
		</div>
	</CardContent>
</Card>
