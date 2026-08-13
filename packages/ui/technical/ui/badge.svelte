<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { type BadgeVariant, badgeVariants } from './badge.svelte.js';
	import { cn } from '../utils.js';

	let {
		class: className,
		variant = 'default',
		children,
		...restProps
	}: HTMLAttributes<HTMLSpanElement> & { variant?: BadgeVariant } = $props();
</script>

<span class={cn(badgeVariants({ variant }), className)} {...restProps}>
	{@render children?.()}
</span>
