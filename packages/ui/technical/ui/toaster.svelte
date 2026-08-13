<script lang="ts">
	import { fly } from 'svelte/transition';
	import { cn } from '../utils.js';
	import { toasts } from './toast.svelte.js';
</script>

<!-- aria-live on the container, not on each toast: the region has to exist before the message is
	 inserted for screen readers to announce it. -->
<div
	aria-live="polite"
	aria-atomic="false"
	class="pointer-events-none fixed inset-x-0 z-50 flex flex-col items-center gap-2 px-4"
	style="bottom: calc(var(--bottom-nav-h, 0px) + 1rem)"
>
	{#each toasts.toasts as item (item.id)}
		<div
			transition:fly={{ y: 12, duration: 180 }}
			class={cn(
				'pointer-events-auto flex w-full max-w-md items-center gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur',
				item.tone === 'destructive'
					? 'border-destructive/40 bg-destructive/10 text-destructive'
					: 'bg-card/95'
			)}
		>
			<span class="flex-1">{item.message}</span>
			{#if item.action}
				<button
					onclick={() => {
						void item.action?.run();
						toasts.dismiss(item.id);
					}}
					class="min-h-8 shrink-0 rounded-md px-2 font-medium text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
				>
					{item.action.label}
				</button>
			{/if}
			<button
				onclick={() => toasts.dismiss(item.id)}
				aria-label="Fermer la notification"
				class="shrink-0 rounded-md px-1 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
			>
				×
			</button>
		</div>
	{/each}
</div>
