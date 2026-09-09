<script lang="ts">
	import { cn } from '../technical/utils.js';
	import Skeleton from '../technical/ui/skeleton.svelte';

	interface Props {
		/** Matches ArticleCard's featured tile so the grid doesn't reflow once loaded. */
		featured?: boolean;
		class?: string;
	}

	let { featured = false, class: className }: Props = $props();
</script>

<div
	data-test-article-card-skeleton
	aria-hidden="true"
	class={cn(
		'flex flex-col overflow-hidden rounded-2xl border bg-card shadow-sm',
		featured ? 'sm:col-span-2 lg:col-span-2' : '',
		className
	)}
>
	<Skeleton class={cn('w-full rounded-none', featured ? 'h-64 sm:h-80' : 'h-36')} />
	<div class="flex flex-1 flex-col gap-2 p-4 pt-5">
		<Skeleton class="h-3 w-24" />
		<Skeleton class="h-4 w-full" />
		<Skeleton class="h-4 w-4/5" />
		<Skeleton class="mt-auto h-3 w-16" />
	</div>
</div>
