<script lang="ts">
	interface Props {
		/** 0 to 1. Values outside the range are clamped rather than overflowing the track. */
		progress: number;
		label?: string;
	}

	let { progress, label = 'Progression de lecture' }: Props = $props();

	const percent = $derived(Math.round(Math.min(Math.max(progress, 0), 1) * 100));
</script>

<div
	role="progressbar"
	aria-label={label}
	aria-valuenow={percent}
	aria-valuemin={0}
	aria-valuemax={100}
	class="fixed inset-x-0 top-0 z-50 h-1 bg-transparent"
>
	<div
		class="h-full bg-primary transition-[width] duration-150 ease-out"
		style={`width: ${percent}%;`}
	></div>
</div>
