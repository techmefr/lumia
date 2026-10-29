<script lang="ts">
	import { untrack } from 'svelte';
	import { Button, Input, Label } from '@lumia/ui';
	import type { ExtensionApi } from '$technical/browser/extension-api';
	import { t } from '$technical/i18n/i18n';
	import {
		hostPermissionPattern,
		normalizeInstanceUrl,
		writeInstanceUrl
	} from '$technical/storage/instance-settings';

	let {
		extension,
		value = '',
		onsaved
	}: { extension: ExtensionApi; value?: string; onsaved: (instanceUrl: string) => void } = $props();

	let address = $state(untrack(() => value));
	let error = $state<string | null>(null);
	let confirmed = $state(false);

	const insecure = $derived(address.trim().toLowerCase().startsWith('http:'));

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		confirmed = false;
		const instanceUrl = normalizeInstanceUrl(address);
		if (instanceUrl === null) {
			error = t('settings.instanceInvalid');
			return;
		}
		const granted = await extension.permissions.request({
			origins: [hostPermissionPattern(instanceUrl)]
		});
		if (!granted) {
			error = t('settings.permissionDenied');
			return;
		}
		const abandoned = await writeInstanceUrl(extension.storage.local, instanceUrl);
		if (abandoned !== null) {
			await extension.permissions.remove({ origins: [hostPermissionPattern(abandoned)] });
		}
		address = instanceUrl;
		error = null;
		confirmed = true;
		onsaved(instanceUrl);
	}
</script>

<form data-test-instance-form class="flex flex-col gap-3" onsubmit={submit}>
	<div class="flex flex-col gap-1.5">
		<Label for="instance-url">{t('settings.instanceLabel')}</Label>
		<Input
			id="instance-url"
			type="url"
			inputmode="url"
			autocomplete="url"
			placeholder="https://"
			aria-describedby="instance-hint"
			bind:value={address}
			required
		/>
		<p id="instance-hint" class="text-xs text-muted-foreground">{t('settings.instanceHint')}</p>
	</div>
	{#if insecure}
		<p data-test-instance-insecure role="status" class="text-sm text-destructive">
			{t('settings.instanceInsecure')}
		</p>
	{/if}
	{#if error}
		<p data-test-instance-error role="alert" class="text-sm text-destructive">{error}</p>
	{/if}
	{#if confirmed}
		<p data-test-instance-saved role="status" class="text-sm text-muted-foreground">
			{t('settings.instanceSaved')}
		</p>
	{/if}
	<Button type="submit">{t('settings.instanceSave')}</Button>
</form>
