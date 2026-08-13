<script lang="ts">
	interface MenuEntry {
		label: string;
		href?: string;
		run?: () => void | Promise<void>;
	}

	interface Props {
		entries: MenuEntry[];
		/** Where a short press goes. A long press (or the arrow) opens the menu instead. */
		href: string;
		label: string;
		icon: import('svelte').Component<{ class?: string }>;
	}

	let { entries, href, label, icon: Icon }: Props = $props();

	const LONG_PRESS_MS = 450;

	let open = $state(false);
	let longPressed = $state(false);
	let timer: ReturnType<typeof setTimeout> | null = null;
	let container = $state<HTMLElement | null>(null);

	function startPress() {
		longPressed = false;
		timer = setTimeout(() => {
			longPressed = true;
			open = true;
		}, LONG_PRESS_MS);
	}

	function endPress() {
		if (timer) clearTimeout(timer);
		timer = null;
	}

	function onLinkClick(event: MouseEvent) {
		// The long press already opened the menu; letting the click through would navigate away.
		if (longPressed) {
			event.preventDefault();
			longPressed = false;
		}
	}

	$effect(() => {
		if (!open) return;
		function onPointerDown(event: PointerEvent) {
			if (container && !container.contains(event.target as Node)) open = false;
		}
		function onKeydown(event: KeyboardEvent) {
			if (event.key === 'Escape') open = false;
		}
		document.addEventListener('pointerdown', onPointerDown);
		document.addEventListener('keydown', onKeydown);
		return () => {
			document.removeEventListener('pointerdown', onPointerDown);
			document.removeEventListener('keydown', onKeydown);
		};
	});
</script>

<div bind:this={container} class="relative flex items-center">
	<a
		{href}
		aria-label={label}
		onpointerdown={startPress}
		onpointerup={endPress}
		onpointerleave={endPress}
		onpointercancel={endPress}
		oncontextmenu={(event) => event.preventDefault()}
		onclick={onLinkClick}
		class="flex min-h-9 min-w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
	>
		<Icon class="size-5" />
	</a>
	<!-- An explicit toggle next to the link: a long press is undiscoverable on its own and
		 unreachable by keyboard. -->
	<button
		onclick={() => (open = !open)}
		aria-expanded={open}
		aria-haspopup="menu"
		aria-label="{label} — plus d'options"
		class="flex min-h-9 w-5 items-center justify-center rounded-md text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
	>
		<span aria-hidden="true" class="text-xs">▾</span>
	</button>

	{#if open}
		<div
			role="menu"
			class="absolute right-0 top-full z-40 mt-1 w-52 overflow-hidden rounded-xl border bg-card py-1 shadow-xl"
		>
			{#each entries as entry (entry.label)}
				{#if entry.href}
					<a
						role="menuitem"
						href={entry.href}
						onclick={() => (open = false)}
						class="flex min-h-10 items-center px-3 text-sm transition-colors hover:bg-secondary"
					>
						{entry.label}
					</a>
				{:else}
					<button
						role="menuitem"
						onclick={() => {
							open = false;
							void entry.run?.();
						}}
						class="flex min-h-10 w-full items-center px-3 text-left text-sm transition-colors hover:bg-secondary"
					>
						{entry.label}
					</button>
				{/if}
			{/each}
		</div>
	{/if}
</div>
