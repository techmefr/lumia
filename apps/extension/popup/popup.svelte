<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Icon } from '@lumia/ui';
	import { Alert02Icon, BookOpen01Icon, BookmarkCheck01Icon, Loading03Icon } from '@hugeicons/core-free-icons';
	import type { ExtensionApi } from '$technical/browser/extension-api';
	import { openReaderPanel } from '$technical/browser/reader-panel';
	import { openLumiaClient } from '$technical/api/lumia-session';
	import { t } from '$technical/i18n/i18n';
	import { savePage, type SaveOutcome } from '$domain/save/save-page';
	import { NEEDS_SETTINGS, OUTCOME_MESSAGE } from '$domain/save/save-feedback';

	let { extension }: { extension: ExtensionApi } = $props();

	let outcome = $state<SaveOutcome | null>(null);

	const succeeded = $derived(outcome === 'saved' || outcome === 'already_saved');

	onMount(async () => {
		const [tab] = await extension.tabs.query({ active: true, currentWindow: true });
		const client = await openLumiaClient(extension.storage.local);
		outcome = await savePage(client, tab?.url);
	});
</script>

<main class="flex flex-col gap-3 p-4">
	<h1 class="font-serif text-lg">Lumia</h1>
	{#if outcome === null}
		<p data-test-popup-status role="status" class="flex items-center gap-2 text-sm text-muted-foreground">
			<Icon icon={Loading03Icon} class="size-4 animate-spin" />
			{t('save.saving')}
		</p>
	{:else}
		<p
			data-test-popup-status
			role={succeeded ? 'status' : 'alert'}
			class="flex items-center gap-2 text-sm {succeeded ? 'text-foreground' : 'text-destructive'}"
		>
			{#if succeeded}
				<Icon icon={BookmarkCheck01Icon} class="size-4 text-primary" />
			{:else}
				<Icon icon={Alert02Icon} class="size-4" />
			{/if}
			{t(OUTCOME_MESSAGE[outcome])}
		</p>
		{#if NEEDS_SETTINGS.has(outcome)}
			<Button data-test-open-settings onclick={() => extension.runtime.openOptionsPage()}>
				{t('popup.openSettings')}
			</Button>
		{/if}
	{/if}
	<Button data-test-open-reader variant="outline" onclick={() => openReaderPanel(extension)}>
		<Icon icon={BookOpen01Icon} />
		{t('popup.openReader')}
	</Button>
</main>
