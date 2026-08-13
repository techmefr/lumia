<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';
	import { cn } from '../utils.js';

	interface Props extends HTMLInputAttributes {
		/** Bindable handle on the underlying element, for callers that need to focus it. */
		ref?: HTMLInputElement | null;
	}

	let {
		class: className,
		value = $bindable(),
		ref = $bindable(null),
		type,
		...restProps
	}: Props = $props();
</script>

<input
	bind:this={ref}
	{type}
	bind:value
	class={cn(
		'flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
		className
	)}
	{...restProps}
/>
