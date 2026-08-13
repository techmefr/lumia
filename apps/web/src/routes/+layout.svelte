<script lang="ts">
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { lumia } from '$lib/client';

	let { children } = $props();

	async function logout() {
		await lumia.user.logout();
		await goto('/login');
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if page.url.pathname !== '/login' && page.url.pathname !== '/onboarding'}
	<nav>
		<a href="/articles">Articles</a>
		<a href="/etincelle">L'Étincelle</a>
		<a href="/feeds">Mes flux</a>
		<button onclick={logout}>Déconnexion</button>
	</nav>
{/if}

<main>
	{@render children()}
</main>

<style>
	nav {
		display: flex;
		gap: 1rem;
		align-items: center;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid #ddd;
	}
	main {
		padding: 1rem;
	}
</style>
