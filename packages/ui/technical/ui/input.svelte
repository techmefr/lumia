<script lang="ts">
	import type { HTMLInputAttributes } from 'svelte/elements';
	import { cn } from '../utils.js';

	let { class: className, value = $bindable(), type, ...restProps }: HTMLInputAttributes = $props();
</script>

<input
	{type}
	bind:value
	class={cn(
		'flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
		className
	)}
	{...restProps}
/>
