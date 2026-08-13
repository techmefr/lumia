<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Button } from '@lumia/ui';
	import Sun from '@lucide/svelte/icons/sun';
	import Moon from '@lucide/svelte/icons/moon';
	import { lumia } from '$technical/api/client';
	import { getTheme, toggleTheme } from '$technical/theme/theme-store.svelte.js';

	let { children } = $props();

	const authRoutes = ['/login', '/onboarding'];

	async function logout() {
		await lumia.user.logout();
		await goto('/login');
	}
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if !authRoutes.includes(page.url.pathname)}
	<header class="border-b bg-card">
		<nav class="mx-auto flex max-w-5xl flex-wrap items-center gap-1 px-4 py-3">
			<span class="mr-4 font-serif text-lg font-semibold">Lumia</span>
			<Button variant="ghost" size="sm" href="/articles">Articles</Button>
			<Button variant="ghost" size="sm" href="/etincelle">L'Étincelle</Button>
			<Button variant="ghost" size="sm" href="/feeds">Mes flux</Button>
			<Button variant="ghost" size="sm" href="/a-lire-plus-tard">À lire plus tard</Button>
			<div class="ml-auto flex items-center gap-1">
				<Button
					variant="ghost"
					size="icon"
					aria-label="Changer de thème"
					onclick={toggleTheme}
				>
					{#if getTheme() === 'dark'}
						<Sun class="size-4" />
					{:else}
						<Moon class="size-4" />
					{/if}
				</Button>
				<Button variant="outline" size="sm" onclick={logout}>Déconnexion</Button>
			</div>
		</nav>
	</header>
{/if}

<main class="mx-auto max-w-5xl px-4 py-6 sm:px-6">
	{@render children()}
</main>
