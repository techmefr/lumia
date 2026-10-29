<script lang="ts">
	import { WifiDisconnected01Icon } from '@hugeicons/core-free-icons';
	import { Icon } from '@lumia/ui';
	import { connectivity } from '$technical/offline/connectivity.svelte';
	import { t } from '$technical/i18n/i18n.svelte';
</script>

{#if !connectivity.online}
	<div
		data-test-offline-banner
		role="status"
		class="flex items-start gap-2 border-b bg-muted px-4 py-2 text-sm text-muted-foreground print:hidden"
	>
		<Icon icon={WifiDisconnected01Icon} class="mt-0.5 size-4 shrink-0" />
		<p>{t('offline.banner')}</p>
	</div>
{/if}
