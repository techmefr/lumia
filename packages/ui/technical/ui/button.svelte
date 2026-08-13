<script lang="ts" module>
	import type { HTMLAnchorAttributes, HTMLButtonAttributes } from 'svelte/elements';
	import { type ButtonSize, type ButtonVariant, buttonVariants } from './button.svelte.js';
	import { cn } from '../utils.js';

	export type ButtonProps = HTMLButtonAttributes &
		Omit<HTMLAnchorAttributes, 'type'> & {
			variant?: ButtonVariant;
			size?: ButtonSize;
			href?: string;
		};
</script>

<script lang="ts">
	let {
		class: className,
		variant = 'default',
		size = 'default',
		type = 'button',
		href,
		children,
		...restProps
	}: ButtonProps = $props();
</script>

{#if href}
	<a
		{href}
		class={cn(buttonVariants({ variant, size }), className)}
		{...restProps as HTMLAnchorAttributes}
	>
		{@render children?.()}
	</a>
{:else}
	<button
		{type}
		class={cn(buttonVariants({ variant, size }), className)}
		{...restProps as HTMLButtonAttributes}
	>
		{@render children?.()}
	</button>
{/if}
