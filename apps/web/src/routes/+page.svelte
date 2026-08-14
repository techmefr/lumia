<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { lumia } from '$technical/api/client';

	onMount(() => {
		void goto(base + (lumia.user.isAuthenticated() ? '/articles' : '/login'));
	});
</script>
