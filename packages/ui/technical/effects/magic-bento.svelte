<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * Bento grid container: cursor-tracked spotlight + tilt on any direct
	 * descendant marked with the `magic-bento-cell` class.
	 */
	type Props = {
		glowColor?: string;
		class?: string;
		children: Snippet;
	};

	let { glowColor = 'var(--primary)', class: className = '', children }: Props = $props();

	function handlePointerMove(event: PointerEvent) {
		const target = event.target as HTMLElement;
		const cell = target.closest<HTMLElement>('.magic-bento-cell');
		if (!cell) return;
		const rect = cell.getBoundingClientRect();
		const x = event.clientX - rect.left;
		const y = event.clientY - rect.top;
		cell.style.setProperty('--mx', `${x}px`);
		cell.style.setProperty('--my', `${y}px`);
		const rotateX = ((y / rect.height - 0.5) * -6).toFixed(2);
		const rotateY = ((x / rect.width - 0.5) * 6).toFixed(2);
		cell.style.setProperty('--rx', `${rotateX}deg`);
		cell.style.setProperty('--ry', `${rotateY}deg`);
	}

	function resetTilt(event: PointerEvent) {
		const target = event.target as HTMLElement;
		const cell = target.closest<HTMLElement>('.magic-bento-cell');
		if (!cell) return;
		cell.style.setProperty('--rx', '0deg');
		cell.style.setProperty('--ry', '0deg');
	}
</script>

<div
	class="magic-bento grid gap-4 {className}"
	style={`--glow-color: ${glowColor}`}
	onpointermove={handlePointerMove}
	onpointerleave={resetTilt}
	role="presentation"
>
	{@render children()}
</div>

<style>
	.magic-bento :global(.magic-bento-cell) {
		position: relative;
		overflow: hidden;
		transform: perspective(800px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg));
		transition: transform 0.2s ease-out;
		will-change: transform;
	}

	.magic-bento :global(.magic-bento-cell)::before {
		content: '';
		position: absolute;
		inset: 0;
		background: radial-gradient(
			220px circle at var(--mx, 50%) var(--my, 50%),
			color-mix(in oklch, var(--glow-color) 20%, transparent),
			transparent 70%
		);
		opacity: 0;
		transition: opacity 0.3s ease-out;
		pointer-events: none;
	}

	.magic-bento :global(.magic-bento-cell:hover)::before {
		opacity: 1;
	}
</style>
