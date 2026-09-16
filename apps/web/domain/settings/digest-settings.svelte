<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, CardContent, Label, toast } from '@lumia/ui';
	import Mail from '@lucide/svelte/icons/mail';
	import type { DigestFrequency, Me } from '@lumia/core';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

	// Derived so the three labels follow a language change like the rest of the screen.
	const FREQUENCIES = $derived<{ value: DigestFrequency; label: string }[]>([
		{ value: 'never', label: t('digest.never') },
		{ value: 'daily', label: t('digest.daily') },
		{ value: 'weekly', label: t('digest.weekly') }
	]);

	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);
	let frequency = $state<DigestFrequency>('never');
	let hour = $state(8);
	let timezone = $state('UTC');

	const isSubscribed = $derived(frequency !== 'never');

	function hourLabel(value: number): string {
		return `${String(value).padStart(2, '0')}:00`;
	}

	function hydrate(next: Me) {
		frequency = next.digest_frequency;
		hour = next.digest_hour;
		timezone = next.digest_timezone;
	}

	async function save() {
		saving = true;
		error = null;
		try {
			// The zone comes from the browser rather than from a picker: it is already the reader's
			// own, and a list of four hundred IANA names is a worse answer than the right default.
			const detected = Intl.DateTimeFormat().resolvedOptions().timeZone;
			hydrate(
				await lumia.user.updateMe({
					digest_frequency: frequency,
					digest_hour: hour,
					digest_timezone: detected || timezone
				})
			);
			toast(t('digest.saved'));
		} catch {
			error = t('digest.saveFailed');
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		lumia.user
			.getMe()
			.then(hydrate)
			.catch(() => {
				error = t('digest.loadFailed');
			})
			.finally(() => {
				loading = false;
			});
	});
</script>

<Card>
	<CardContent class="flex flex-col gap-5 pt-6">
		<div>
			<h2 id="digest" class="flex items-center gap-2 text-lg font-semibold">
				<Mail class="size-5 text-primary" />
				{t('digest.title')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">{t('digest.intro')}</p>
		</div>

		{#if error}
			<p data-test-digest-error class="text-sm text-destructive">{error}</p>
		{/if}

		{#if !loading}
			<div class="flex flex-col gap-2">
				<Label for="digest-frequency">{t('digest.frequency')}</Label>
				<select
					id="digest-frequency"
					data-test-digest-frequency
					bind:value={frequency}
					class="h-10 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					{#each FREQUENCIES as option (option.value)}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
			</div>

			{#if isSubscribed}
				<div class="flex flex-col gap-2">
					<Label for="digest-hour">{t('digest.hour')}</Label>
					<select
						id="digest-hour"
						data-test-digest-hour
						bind:value={hour}
						class="h-10 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					>
						{#each HOURS as value (value)}
							<option value={value}>{hourLabel(value)}</option>
						{/each}
					</select>
					<p class="text-xs text-muted-foreground">
						{t('digest.timezone', { zone: timezone })}
					</p>
				</div>

				<p class="text-xs text-muted-foreground">{t('digest.emptyHint')}</p>
				{#if frequency === 'weekly'}
					<p class="text-xs text-muted-foreground">{t('digest.weeklyHint')}</p>
				{/if}
			{/if}

			<Button data-test-digest-save class="self-start" disabled={saving} onclick={save}>
				{t('common.save')}
			</Button>
		{/if}
	</CardContent>
</Card>
