<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements';
	import { cn } from '../utils.js';

	interface Props extends HTMLAttributes<HTMLDivElement> {
		level?: 1 | 2 | 3 | 4 | 5 | 6;
	}

	let { class: className, children, level = 3, ...restProps }: Props = $props();
</script>

<div
	role="heading"
	aria-level={level}
	class={cn('font-semibold leading-none', className)}
	{...restProps}
>
	{@render children?.()}
</div>
