<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, CardContent, CardHeader, CardTitle } from '@lumia/ui';
	import type { ExtensionApi } from '$technical/browser/extension-api';
	import { t } from '$technical/i18n/i18n';
	import { readInstanceUrl } from '$technical/storage/instance-settings';
	import AccountPanel from './account-panel.svelte';
	import InstanceForm from './instance-form.svelte';

	let { extension }: { extension: ExtensionApi } = $props();

	let instanceUrl = $state<string | null>(null);
	let loaded = $state(false);

	onMount(async () => {
		instanceUrl = await readInstanceUrl(extension.storage.local);
		loaded = true;
	});
</script>

<main class="mx-auto flex max-w-md flex-col gap-4 p-6">
	<h1 class="text-2xl">{t('settings.title')}</h1>
	{#if loaded}
		<Card>
			<CardHeader>
				<CardTitle class="text-base">{t('settings.instanceTitle')}</CardTitle>
			</CardHeader>
			<CardContent>
				<InstanceForm
					{extension}
					value={instanceUrl ?? ''}
					onsaved={(saved) => (instanceUrl = saved)}
				/>
			</CardContent>
		</Card>
		<Card>
			<CardHeader>
				<CardTitle class="text-base">{t('settings.signInTitle')}</CardTitle>
			</CardHeader>
			<CardContent>
				<AccountPanel {extension} {instanceUrl} />
			</CardContent>
		</Card>
	{/if}
</main>
