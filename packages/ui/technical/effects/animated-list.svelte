<script lang="ts" generics="T">
	import type { Snippet } from 'svelte';

	type Props = {
		items: T[];
		getKey?: (item: T, index: number) => string | number;
		staggerMs?: number;
		class?: string;
		children: Snippet<[T, number]>;
	};

	let { items, getKey, staggerMs = 40, class: className = '', children }: Props = $props();
</script>

<div data-test-animated-list class="flex flex-col gap-0.5 {className}">
	{#each items as item, index (getKey ? getKey(item, index) : index)}
		<div
			data-test-animated-item={index}
			class="animate-in fade-in slide-in-from-left-2 duration-300 ease-out"
			style={`animation-delay: ${index * staggerMs}ms`}
		>
			{@render children(item, index)}
		</div>
	{/each}
</div>
