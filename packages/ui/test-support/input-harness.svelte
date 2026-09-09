<script lang="ts">
	import Input from '../technical/ui/input.svelte';

	// A harness rather than reaching into the component: `$bindable` props are not exports, so the
	// only way to observe a binding is to be the parent that binds it and report what arrived.
	let value = $state('');
	let ref = $state<HTMLInputElement | null>(null);
</script>

<Input bind:value bind:ref />

<output data-test-bound-value>{value}</output>
<output data-test-ref-tag>{ref ? ref.tagName : 'none'}</output>
