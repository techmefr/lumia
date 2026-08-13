<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { lumia } from '$technical/api/client';

	onMount(() => {
		void goto(lumia.user.isAuthenticated() ? '/articles' : '/login');
	});
</script>
