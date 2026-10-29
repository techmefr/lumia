<script lang="ts">
	import { Button, Input, Label } from '@lumia/ui';
	import { apiBaseUrl } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';
	import {
		instanceHost,
		isSecureInstanceUrl,
		normalizeInstanceUrl,
		storeInstanceUrl
	} from '$technical/instance/instance-url';

	let value = $state(apiBaseUrl);
	let invalid = $state(false);
	let insecure = $state(false);

	const host = $derived.by(() => {
		const url = normalizeInstanceUrl(value);
		return url === null ? null : instanceHost(url);
	});

	function save(event: SubmitEvent) {
		event.preventDefault();
		const url = normalizeInstanceUrl(value);
		invalid = url === null;
		insecure = url !== null && !isSecureInstanceUrl(url);
		if (url === null || insecure) return;
		storeInstanceUrl(localStorage, url);
		location.reload();
	}
</script>

<form data-test-instance-form class="flex flex-col gap-2" onsubmit={save}>
	<Label for="instance-url">{t('instance.label')}</Label>
	<Input
		id="instance-url"
		data-test-instance-url
		type="url"
		inputmode="url"
		autocomplete="url"
		placeholder="https://lumia.example.com/api"
		bind:value
		aria-invalid={invalid}
		aria-describedby="instance-url-hint"
		required
	/>
	<p id="instance-url-hint" class="text-xs text-muted-foreground">{t('instance.hint')}</p>
	{#if host}
		<p data-test-instance-host class="text-xs text-muted-foreground">
			{t('instance.connectingTo', { host })}
		</p>
	{/if}
	{#if insecure}
		<p data-test-instance-insecure role="alert" class="text-sm text-destructive">
			{t('instance.insecure')}
		</p>
	{/if}
	{#if invalid}
		<p data-test-instance-invalid role="alert" class="text-sm text-destructive">
			{t('instance.invalid')}
		</p>
	{/if}
	<Button type="submit" variant="outline" data-test-instance-save>{t('instance.save')}</Button>
</form>
