<script lang="ts">
	import MagicBento from '../technical/effects/magic-bento.svelte';

	// A harness because the component takes a required snippet, which cannot be written from a .ts
	// test file — and because the effect is only observable on a cell it is given.
	let { glowColor, class: className }: { glowColor?: string; class?: string } = $props();
</script>

<MagicBento {glowColor} class={className}>
	<div data-test-cell="a" class="magic-bento-cell">
		<span data-test-inner>Actualités</span>
	</div>
	<div data-test-cell="b" class="magic-bento-cell">Bricolage</div>
	<div data-test-plain>Hors grille</div>
</MagicBento>
