<script lang="ts">
	type Props = {
		color?: string;
		speed?: number;
		alwaysOn?: boolean;
		class?: string;
	};

	let { color = 'var(--primary)', speed = 4, alwaysOn = true, class: className = '' }: Props =
		$props();
</script>

<div
	data-test-border-glow
	aria-hidden="true"
	class="pointer-events-none absolute -inset-1 -z-10 rounded-[inherit] transition-opacity duration-500 {alwaysOn
		? 'opacity-70'
		: 'opacity-0 group-hover:opacity-70'} {className}"
	style={`background: conic-gradient(from 0deg, transparent 0deg, ${color} 70deg, transparent 160deg, transparent 360deg); filter: blur(14px); animation: lumia-border-glow-spin ${speed}s linear infinite;`}
></div>

<style>
	@keyframes lumia-border-glow-spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
