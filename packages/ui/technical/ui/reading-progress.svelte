<script lang="ts">
	interface Props {
		/** 0 to 1. Values outside the range are clamped rather than overflowing the track. */
		progress: number;
		/** Passed in by the app, which owns the translations; the default keeps the package standalone. */
		label?: string;
	}

	let { progress, label = 'Reading progress' }: Props = $props();

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
		data-test-progress-bar
		class="h-full bg-primary transition-[width] duration-150 ease-out"
		style={`width: ${percent}%;`}
	></div>
</div>
