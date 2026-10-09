<script lang="ts">
	import WifiOff from '@lucide/svelte/icons/wifi-off';
	import { t } from '$technical/i18n/i18n.svelte';
</script>

<div
	data-test-offline-banner
	role="status"
	class="flex items-center justify-center gap-1.5 border-b bg-secondary px-4 py-1.5 text-center text-xs font-medium text-secondary-foreground"
>
	<WifiOff class="size-3.5" />
	{t('offline.banner')}
</div>
