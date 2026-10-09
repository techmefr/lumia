<script lang="ts">
	import HardDrive from '@lucide/svelte/icons/hard-drive';
	import { t } from '$technical/i18n/i18n.svelte';
	import { formatBytes } from './format-bytes';

	interface Props {
		bytesUsed: number;
		capBytes: number;
		articleCount: number;
	}

	let { bytesUsed, capBytes, articleCount }: Props = $props();

	const percent = $derived(capBytes > 0 ? Math.min((bytesUsed / capBytes) * 100, 100) : 0);
</script>

<div data-test-offline-storage class="flex flex-col gap-1.5">
	<div class="flex items-center justify-between gap-2 text-sm text-muted-foreground">
		<span class="flex items-center gap-1.5">
			<HardDrive class="size-4" />
			{t('offline.storageUsed', { used: formatBytes(bytesUsed), cap: formatBytes(capBytes) })}
		</span>
		<span>{t('offline.articleCount', { count: articleCount })}</span>
	</div>
	<div class="h-1.5 w-full overflow-hidden rounded-full bg-muted">
		<div
			data-test-offline-storage-bar
			class="h-full rounded-full bg-primary transition-[width] duration-200 ease-out"
			style={`width: ${percent}%;`}
		></div>
	</div>
</div>
