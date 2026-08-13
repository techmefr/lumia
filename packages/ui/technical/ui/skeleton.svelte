<script lang="ts">
	import { cn } from '../utils.js';

	interface Props {
		class?: string;
	}

	let { class: className }: Props = $props();
</script>

<!-- Decorative: the surrounding region announces the loading state via role="status". -->
<div aria-hidden="true" class={cn('animate-pulse rounded-md bg-muted', className)}></div>
