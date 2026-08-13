<script module lang="ts">
	type Position = 'top' | 'bottom' | 'left' | 'right';
	type Curve = 'linear' | 'bezier' | 'ease-in' | 'ease-out' | 'ease-in-out';

	const CURVE_FUNCTIONS: Record<Curve, (p: number) => number> = {
		linear: (p) => p,
		bezier: (p) => p * p * (3 - 2 * p),
		'ease-in': (p) => p * p,
		'ease-out': (p) => 1 - Math.pow(1 - p, 2),
		'ease-in-out': (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2)
	};

	function gradientDir(pos: Position): string {
		return { top: 'to top', bottom: 'to bottom', left: 'to left', right: 'to right' }[pos];
	}
</script>

<script lang="ts">
	type Props = {
		position?: Position;
		strength?: number;
		height?: string;
		width?: string;
		divCount?: number;
		exponential?: boolean;
		zIndex?: number;
		opacity?: number;
		curve?: Curve;
		target?: 'parent' | 'page';
		class?: string;
	};

	let {
		position = 'bottom',
		strength = 2,
		height = '6rem',
		width = undefined,
		divCount = 5,
		exponential = false,
		zIndex = 30,
		opacity = 1,
		curve = 'linear',
		target = 'parent',
		class: className = ''
	}: Props = $props();

	const divs = $derived.by(() => {
		const out: { style: string }[] = [];
		const inc = 100 / divCount;
		const curveFn = CURVE_FUNCTIONS[curve] || CURVE_FUNCTIONS.linear;
		for (let i = 1; i <= divCount; i++) {
			let progress = i / divCount;
			progress = curveFn(progress);
			const blur = exponential
				? Math.pow(2, progress * 4) * 0.0625 * strength
				: 0.0625 * (progress * divCount + 1) * strength;
			const p1 = Math.round((inc * i - inc) * 10) / 10;
			const p2 = Math.round(inc * i * 10) / 10;
			const p3 = Math.round((inc * i + inc) * 10) / 10;
			const p4 = Math.round((inc * i + inc * 2) * 10) / 10;
			let grad = `transparent ${p1}%, black ${p2}%`;
			if (p3 <= 100) grad += `, black ${p3}%`;
			if (p4 <= 100) grad += `, transparent ${p4}%`;
			const dir = gradientDir(position);
			out.push({
				style: `mask-image:linear-gradient(${dir}, ${grad});-webkit-mask-image:linear-gradient(${dir}, ${grad});backdrop-filter:blur(${blur.toFixed(3)}rem);-webkit-backdrop-filter:blur(${blur.toFixed(3)}rem);opacity:${opacity};`
			});
		}
		return out;
	});

	const containerStyle = $derived.by(() => {
		const isVertical = position === 'top' || position === 'bottom';
		const isPage = target === 'page';
		const parts: string[] = [
			`position:${isPage ? 'fixed' : 'absolute'}`,
			'pointer-events:none',
			`z-index:${isPage ? zIndex + 100 : zIndex}`
		];
		if (isVertical) {
			parts.push(`height:${height}`);
			parts.push(`width:${width || '100%'}`);
			parts.push(`${position}:0`, 'left:0', 'right:0');
		} else {
			parts.push(`width:${width || height}`);
			parts.push('height:100%');
			parts.push(`${position}:0`, 'top:0', 'bottom:0');
		}
		return parts.join(';') + ';';
	});
</script>

<div class="gradual-blur relative isolate {className}" style={containerStyle}>
	<div class="relative h-full w-full">
		{#each divs as d, i (i)}
			<div class="absolute inset-0" style={d.style}></div>
		{/each}
	</div>
</div>
