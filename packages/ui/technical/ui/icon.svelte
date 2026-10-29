<script lang="ts">
	import { HugeiconsIcon, type IconSvgElement } from '@hugeicons/svelte';

	interface Props {
		icon: IconSvgElement;
		size?: number | string;
		strokeWidth?: number;
		label?: string;
		class?: string;
	}

	let { icon, size, strokeWidth, label, class: className }: Props = $props();
</script>

{#if label}
	<HugeiconsIcon {icon} {size} {strokeWidth} class={className} role="img" aria-label={label} />
{:else}
	<HugeiconsIcon {icon} {size} {strokeWidth} class={className} aria-hidden="true" focusable="false" />
{/if}
