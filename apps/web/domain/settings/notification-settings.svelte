<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, CardContent, Label, toast } from '@lumia/ui';
	import Bell from '@lucide/svelte/icons/bell';
	import BellOff from '@lucide/svelte/icons/bell-off';
	import Moon from '@lucide/svelte/icons/moon';
	import {
		INTERVAL_OPTIONS,
		getNotificationSettings,
		permissionState,
		requestPermission,
		updateNotificationSettings,
		type PermissionState
	} from '$technical/notifications/notification-store.svelte.js';
	import { t } from '$technical/i18n/i18n.svelte.js';

	const HOURS = Array.from({ length: 24 }, (_, hour) => hour);

	let permission = $state<PermissionState>('default');
	let enabled = $state(false);
	let intervalMinutes = $state(30);
	let threshold = $state(3);
	let quietFromHour = $state(22);
	let quietToHour = $state(8);

	const isBlocked = $derived(permission === 'denied' || permission === 'unsupported');

	function hourLabel(hour: number): string {
		return `${String(hour).padStart(2, '0')}:00`;
	}

	async function toggle() {
		if (enabled) {
			enabled = false;
			updateNotificationSettings({ enabled: false });
			return;
		}
		// The browser only grants permission from a user gesture, so it is asked for here rather than
		// on mount.
		permission = await requestPermission();
		if (permission !== 'granted') {
			toast(t('notifications.refused'), { tone: 'destructive' });
			return;
		}
		enabled = true;
		updateNotificationSettings({ enabled: true });
		toast(t('notifications.enabled'));
	}

	function save() {
		updateNotificationSettings({ intervalMinutes, threshold, quietFromHour, quietToHour });
		toast(t('notifications.saved'));
	}

	onMount(() => {
		permission = permissionState();
		const settings = getNotificationSettings();
		// A permission revoked in the browser wins over what was stored here.
		enabled = settings.enabled && permission === 'granted';
		intervalMinutes = settings.intervalMinutes;
		threshold = settings.threshold;
		quietFromHour = settings.quietFromHour;
		quietToHour = settings.quietToHour;
	});
</script>

<Card>
	<CardContent class="flex flex-col gap-5 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-lg font-semibold">
				<Bell class="size-5 text-primary" />
				{t('notifications.title')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">{t('notifications.intro')}</p>
		</div>

		{#if permission === 'unsupported'}
			<p data-test-notif-unsupported class="flex items-center gap-2 text-sm text-muted-foreground">
				<BellOff class="size-4" />
				{t('notifications.unsupported')}
			</p>
		{:else if permission === 'denied'}
			<p data-test-notif-denied class="flex items-center gap-2 text-sm text-destructive">
				<BellOff class="size-4" />
				{t('notifications.denied')}
			</p>
		{/if}

		<Button
			data-test-notif-toggle
			variant={enabled ? 'secondary' : 'default'}
			class="self-start"
			disabled={isBlocked}
			onclick={toggle}
		>
			{#if enabled}
				<BellOff class="size-4" />
				{t('notifications.disable')}
			{:else}
				<Bell class="size-4" />
				{t('notifications.enable')}
			{/if}
		</Button>

		<div class="flex flex-col gap-2">
			<Label for="notif-interval">{t('notifications.frequency')}</Label>
			<select
				id="notif-interval"
				data-test-notif-interval
				bind:value={intervalMinutes}
				class="h-10 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			>
				{#each INTERVAL_OPTIONS as minutes (minutes)}
					<option value={minutes}>
						{minutes < 60
							? t('notifications.everyMinutes', { count: minutes })
							: t('notifications.everyHours', { count: minutes / 60 })}
					</option>
				{/each}
			</select>
		</div>

		<div class="flex flex-col gap-2">
			<Label for="notif-threshold">{t('notifications.threshold')}</Label>
			<select
				id="notif-threshold"
				data-test-notif-threshold
				bind:value={threshold}
				class="h-10 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			>
				{#each [1, 3, 5, 10] as count (count)}
					<option value={count}>
						{count === 1
							? t('notifications.thresholdFirst')
							: t('notifications.thresholdCount', { count })}
					</option>
				{/each}
			</select>
			<p class="text-xs text-muted-foreground">
				{t('notifications.thresholdHint')}
			</p>
		</div>

		<fieldset class="flex flex-col gap-2">
			<legend class="mb-1 flex items-center gap-2 text-sm font-medium">
				<Moon class="size-4" />
				{t('notifications.quietHours')}
			</legend>
			<div class="flex flex-wrap items-end gap-2">
				<label class="flex flex-col gap-1 text-sm">
					<span class="text-muted-foreground">{t('notifications.quietFrom')}</span>
					<select
						data-test-notif-quiet-from
						bind:value={quietFromHour}
						class="h-10 rounded-md border border-input bg-background px-3 text-sm"
					>
						{#each HOURS as hour (hour)}
							<option value={hour}>{hourLabel(hour)}</option>
						{/each}
					</select>
				</label>
				<label class="flex flex-col gap-1 text-sm">
					<span class="text-muted-foreground">{t('notifications.quietTo')}</span>
					<select
						data-test-notif-quiet-to
						bind:value={quietToHour}
						class="h-10 rounded-md border border-input bg-background px-3 text-sm"
					>
						{#each HOURS as hour (hour)}
							<option value={hour}>{hourLabel(hour)}</option>
						{/each}
					</select>
				</label>
			</div>
			<p class="text-xs text-muted-foreground">
				{t('notifications.quietHint')}
			</p>
		</fieldset>

		<Button data-test-notif-save class="self-start" onclick={save}>{t('common.save')}</Button>
	</CardContent>
</Card>
