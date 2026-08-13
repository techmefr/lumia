<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '../utils.js';

	let { class: className, children, ...restProps }: HTMLAttributes<HTMLDivElement> = $props();
</script>

<div
	class={cn('rounded-xl border bg-card text-card-foreground shadow-sm', className)}
	{...restProps}
>
	{@render children?.()}
</div>
