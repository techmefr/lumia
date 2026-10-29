<script lang="ts">
	import { Card, CardContent, Label, toast, Icon } from '@lumia/ui';
	import { WifiDisconnected01Icon } from '@hugeicons/core-free-icons';
	import { t } from '$technical/i18n/i18n.svelte';
	import {
		OFFLINE_LIMIT_OPTIONS,
		getOfflineLimit,
		setOfflineLimit
	} from '$technical/offline/offline-limit';
	import { runOfflineSync } from '$technical/offline/offline-runner';

	let limit = $state(getOfflineLimit());

	function save() {
		setOfflineLimit(limit);
		void runOfflineSync(true);
		toast(t('offline.limitSaved'));
	}
</script>

<Card>
	<CardContent class="flex flex-col gap-4 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-lg font-semibold">
				<Icon icon={WifiDisconnected01Icon} class="size-5 text-primary" />
				{t('offline.settingsTitle')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">{t('offline.settingsDescription')}</p>
		</div>

		<div class="flex flex-col gap-2">
			<Label for="offline-limit">{t('offline.limitLabel')}</Label>
			<select
				id="offline-limit"
				data-test-offline-limit
				bind:value={limit}
				onchange={save}
				class="h-10 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			>
				{#each OFFLINE_LIMIT_OPTIONS as option (option)}
					<option value={option}>
						{option === 0 ? t('offline.limitOff') : t('offline.limitOption', { count: option })}
					</option>
				{/each}
			</select>
		</div>
	</CardContent>
</Card>
