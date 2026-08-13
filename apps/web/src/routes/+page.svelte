<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { lumia } from '$lib/client';

	onMount(() => {
		void goto(lumia.user.isAuthenticated() ? '/articles' : '/login');
	});
</script>
