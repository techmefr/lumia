<script lang="ts">
	import WifiOff from '@lucide/svelte/icons/wifi-off';
	import { connectivity } from '$technical/offline/connectivity.svelte';
	import { t } from '$technical/i18n/i18n.svelte';
</script>

{#if !connectivity.online}
	<div
		data-test-offline-banner
		role="status"
		class="flex items-start gap-2 border-b bg-muted px-4 py-2 text-sm text-muted-foreground print:hidden"
	>
		<WifiOff class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
		<p>{t('offline.banner')}</p>
	</div>
{/if}
