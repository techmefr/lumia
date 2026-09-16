<script lang="ts" module>
	import type { Component } from 'svelte';

	export interface OrbitAction {
		id: string;
		label: string;
		icon: Component;
		/** Set only on actions that toggle, which makes the item a checkbox rather than a command. */
		active?: boolean;
		run: () => void;
	}
</script>

<script lang="ts">
	import { tick } from 'svelte';
	import type { OrbitPosition } from '@lumia/core';
	import Orbit from '@lucide/svelte/icons/orbit';
	import X from '@lucide/svelte/icons/x';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		position: OrbitPosition;
		actions: OrbitAction[];
	}

	let { position, actions }: Props = $props();

	let open = $state(false);
	let container = $state<HTMLElement | null>(null);
	let trigger = $state<HTMLButtonElement | null>(null);
	let menu = $state<HTMLElement | null>(null);

	const isLeft = $derived(position === 'left');

	function items(): HTMLButtonElement[] {
		if (!menu) return [];
		return [...menu.querySelectorAll<HTMLButtonElement>('[data-test-orbit-action]')];
	}

	function focusAt(index: number) {
		const all = items();
		if (all.length === 0) return;
		// Wraps both ways, so holding one arrow key never dead-ends at an edge.
		all[(index + all.length) % all.length].focus();
	}

	function close(returnFocus: boolean) {
		open = false;
		if (returnFocus) trigger?.focus();
	}

	/** The menu is only in the dom once `open` is true, so the focus waits for that render. */
	async function openAt(index: number) {
		open = true;
		await tick();
		focusAt(index);
	}

	function toggle() {
		if (open) {
			open = false;
			return;
		}
		void openAt(0);
	}

	function runAction(action: OrbitAction) {
		action.run();
		close(true);
	}

	function onMenuKeydown(event: KeyboardEvent) {
		const all = items();
		const current = all.indexOf(document.activeElement as HTMLButtonElement);

		if (event.key === 'Escape') {
			event.preventDefault();
			close(true);
			return;
		}
		if (event.key === 'ArrowDown') {
			event.preventDefault();
			focusAt(current + 1);
			return;
		}
		if (event.key === 'ArrowUp') {
			event.preventDefault();
			focusAt(current - 1);
			return;
		}
		if (event.key === 'Home') {
			event.preventDefault();
			focusAt(0);
			return;
		}
		if (event.key === 'End') {
			event.preventDefault();
			focusAt(all.length - 1);
		}
	}

	// Down and up open the menu on its first and last action, the way a menu button is expected to.
	function onTriggerKeydown(event: KeyboardEvent) {
		if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return;
		event.preventDefault();
		const index = event.key === 'ArrowDown' ? 0 : -1;
		if (open) {
			focusAt(index);
			return;
		}
		void openAt(index);
	}

	$effect(() => {
		if (!open) return;
		function onPointerDown(event: PointerEvent) {
			if (container && !container.contains(event.target as Node)) open = false;
		}
		document.addEventListener('pointerdown', onPointerDown);
		return () => document.removeEventListener('pointerdown', onPointerDown);
	});
</script>

<!-- Sits clear of both the mobile navigation and the fixed opinion bar above it, so it never
	 covers a control or the end of the article. -->
<div
	bind:this={container}
	data-test-orbit
	data-position={position}
	class="fixed z-40 flex flex-col {isLeft ? 'left-4 items-start' : 'right-4 items-end'}"
	style="bottom: calc(var(--bottom-nav-h, 0px) + 5rem)"
>
	{#if open}
		<div
			bind:this={menu}
			data-test-orbit-menu
			role="menu"
			tabindex="-1"
			aria-orientation="vertical"
			aria-label={t('orbit.menuLabel')}
			onkeydown={onMenuKeydown}
			class="mb-3 flex animate-in flex-col gap-1.5 rounded-2xl border bg-card/95 p-2 shadow-xl backdrop-blur fade-in slide-in-from-bottom-2 duration-200 {isLeft
				? 'items-start'
				: 'items-end'}"
		>
			{#each actions as action (action.id)}
				<button
					data-test-orbit-action={action.id}
					role={action.active === undefined ? 'menuitem' : 'menuitemcheckbox'}
					aria-checked={action.active === undefined ? undefined : action.active}
					tabindex="-1"
					onclick={() => runAction(action)}
					class="flex min-h-11 w-full items-center gap-2.5 rounded-xl px-3 text-sm whitespace-nowrap transition-colors hover:bg-secondary focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none {action.active
						? 'text-primary'
						: 'text-foreground'} {isLeft ? 'flex-row' : 'flex-row-reverse'}"
				>
					<action.icon class="size-5 shrink-0" />
					<span>{action.label}</span>
				</button>
			{/each}
		</div>
	{/if}

	<button
		bind:this={trigger}
		data-test-orbit-toggle
		onclick={toggle}
		onkeydown={onTriggerKeydown}
		aria-expanded={open}
		aria-haspopup="menu"
		aria-label={open ? t('orbit.close') : t('orbit.open')}
		class="flex size-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg transition-transform hover:scale-105 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:outline-none"
	>
		{#if open}
			<X class="size-6" />
		{:else}
			<Orbit class="size-6" />
		{/if}
	</button>
</div>
