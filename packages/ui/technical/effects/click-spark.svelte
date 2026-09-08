<script lang="ts">
	import type { Snippet } from 'svelte';

	type Easing = 'linear' | 'ease-in' | 'ease-out' | 'ease-in-out';
	type Spark = { x: number; y: number; angle: number; startTime: number };

	type Props = {
		children?: Snippet;
		sparkColor?: string;
		sparkSize?: number;
		sparkRadius?: number;
		sparkCount?: number;
		duration?: number;
		easing?: Easing;
		extraScale?: number;
		class?: string;
	};

	let {
		children,
		sparkColor = '#fff',
		sparkSize = 8,
		sparkRadius = 12,
		sparkCount = 8,
		duration = 350,
		easing = 'ease-out',
		extraScale = 1.0,
		class: className = ''
	}: Props = $props();

	let canvas: HTMLCanvasElement;
	let wrapper: HTMLDivElement;
	const sparks: Spark[] = [];

	function easeFunc(t: number): number {
		switch (easing) {
			case 'linear':
				return t;
			case 'ease-in':
				return t * t;
			case 'ease-in-out':
				return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
			default:
				return t * (2 - t);
		}
	}

	$effect(() => {
		if (!canvas) return;
		// Canvas animation is driven by requestAnimationFrame, so the global
		// prefers-reduced-motion CSS block can't reach it — skip it outright here.
		if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

		const resizeCanvas = () => {
			const width = window.innerWidth;
			const height = window.innerHeight;
			if (canvas.width !== width || canvas.height !== height) {
				canvas.width = width;
				canvas.height = height;
			}
		};
		window.addEventListener('resize', resizeCanvas);
		resizeCanvas();

		const ctx = canvas.getContext('2d');
		if (!ctx) return;
		const resolvedColor = resolveColor(sparkColor);
		let raf = 0;
		const draw = (timestamp: number) => {
			ctx.clearRect(0, 0, canvas.width, canvas.height);
			for (let i = sparks.length - 1; i >= 0; i--) {
				const spark = sparks[i];
				const elapsed = timestamp - spark.startTime;
				if (elapsed >= duration) {
					sparks.splice(i, 1);
					continue;
				}
				const progress = elapsed / duration;
				const eased = easeFunc(progress);
				const distance = eased * sparkRadius * extraScale;
				const lineLength = sparkSize * (1 - eased);
				const x1 = spark.x + distance * Math.cos(spark.angle);
				const y1 = spark.y + distance * Math.sin(spark.angle);
				const x2 = spark.x + (distance + lineLength) * Math.cos(spark.angle);
				const y2 = spark.y + (distance + lineLength) * Math.sin(spark.angle);
				ctx.strokeStyle = resolvedColor;
				ctx.lineWidth = 2;
				ctx.beginPath();
				ctx.moveTo(x1, y1);
				ctx.lineTo(x2, y2);
				ctx.stroke();
			}
			raf = requestAnimationFrame(draw);
		};
		raf = requestAnimationFrame(draw);

		return () => {
			window.removeEventListener('resize', resizeCanvas);
			cancelAnimationFrame(raf);
		};
	});

	function resolveColor(color: string): string {
		if (!color.includes('var(')) return color;
		const probe = document.createElement('span');
		probe.style.color = color;
		document.body.appendChild(probe);
		const resolved = getComputedStyle(probe).color;
		probe.remove();
		return resolved;
	}

	function handleClick(e: MouseEvent) {
		if (!canvas) return;
		const rect = canvas.getBoundingClientRect();
		const x = e.clientX - rect.left;
		const y = e.clientY - rect.top;
		const now = performance.now();
		for (let i = 0; i < sparkCount; i++) {
			sparks.push({ x, y, angle: (2 * Math.PI * i) / sparkCount, startTime: now });
		}
	}
</script>

<svelte:window onclick={handleClick} />

<div bind:this={wrapper} class="contents {className}">
	<canvas
		bind:this={canvas}
		aria-hidden="true"
		class="pointer-events-none fixed inset-0"
		style="width:100vw;height:100dvh;z-index:var(--z-effects, 80);"
	></canvas>
	{#if children}{@render children()}{/if}
</div>
