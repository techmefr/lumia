<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { Button } from '@lumia/ui';
	import Sun from '@lucide/svelte/icons/sun';
	import Moon from '@lucide/svelte/icons/moon';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Rss from '@lucide/svelte/icons/rss';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import LogOut from '@lucide/svelte/icons/log-out';
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
	<header class="animate-in border-b bg-card fade-in slide-in-from-top-2 duration-300">
		<nav class="mx-auto flex max-w-5xl flex-wrap items-center gap-1 px-4 py-3">
			<span class="mr-4 flex items-center gap-1.5 font-serif text-lg font-semibold">
				<Sparkles class="size-5 text-primary transition-transform duration-300 hover:rotate-12" />
				Lumia
			</span>
			<Button variant="ghost" size="sm" href="/articles">
				<Newspaper class="size-4" />
				Articles
			</Button>
			<Button variant="ghost" size="sm" href="/etincelle">
				<Sparkles class="size-4" />
				L'Étincelle
			</Button>
			<Button variant="ghost" size="sm" href="/feeds">
				<Rss class="size-4" />
				Mes flux
			</Button>
			<Button variant="ghost" size="sm" href="/a-lire-plus-tard">
				<Bookmark class="size-4" />
				À lire plus tard
			</Button>
			<div class="ml-auto flex items-center gap-1">
				<Button
					variant="ghost"
					size="icon"
					aria-label="Changer de thème"
					onclick={toggleTheme}
				>
					{#if getTheme() === 'dark'}
						<Sun class="size-4 animate-in spin-in-45 duration-300" />
					{:else}
						<Moon class="size-4 animate-in spin-in-45 duration-300" />
					{/if}
				</Button>
				<Button variant="outline" size="sm" onclick={logout}>
					<LogOut class="size-4" />
					Déconnexion
				</Button>
			</div>
		</nav>
	</header>
{/if}

<main class="mx-auto max-w-5xl animate-in px-4 py-6 fade-in duration-500 sm:px-6">
	{@render children()}
</main>
