<script lang="ts">
	import AnimatedList from '../technical/effects/animated-list.svelte';

	// A harness because the component's children are a snippet, which cannot be written from a .ts
	// test file. It also lets the test see the index the snippet is handed.
	interface Item {
		id: string;
		label: string;
	}

	let {
		items,
		getKey,
		staggerMs,
		class: className
	}: {
		items: Item[];
		getKey?: (item: Item, index: number) => string | number;
		staggerMs?: number;
		class?: string;
	} = $props();
</script>

<AnimatedList {items} {getKey} {staggerMs} class={className}>
	{#snippet children(item: Item, index: number)}
		<span data-test-item={item.id} data-test-index={index}>{item.label}</span>
	{/snippet}
</AnimatedList>
