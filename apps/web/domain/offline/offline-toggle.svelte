<script lang="ts">
	import Download from '@lucide/svelte/icons/download';
	import CircleCheck from '@lucide/svelte/icons/circle-check';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articleId: string;
		offline: boolean;
		pending?: boolean;
		onToggle: () => void;
	}

	let { articleId, offline, pending = false, onToggle }: Props = $props();
</script>

<button
	type="button"
	data-test-offline-toggle={articleId}
	aria-pressed={offline}
	disabled={pending}
	title={offline ? t('offline.removeTitle') : t('offline.makeAvailableTitle')}
	aria-label={offline ? t('offline.removeTitle') : t('offline.makeAvailableTitle')}
	onclick={onToggle}
	class="flex items-center justify-center rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-60"
	class:text-primary={offline}
>
	{#if pending}
		<LoaderCircle class="size-4 animate-spin" />
	{:else if offline}
		<CircleCheck class="size-4" />
	{:else}
		<Download class="size-4" />
	{/if}
</button>
