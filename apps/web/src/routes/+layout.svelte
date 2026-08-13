<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { onMount } from 'svelte';
	import { goto, onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { Button } from '@lumia/ui';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Rss from '@lucide/svelte/icons/rss';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import LogOut from '@lucide/svelte/icons/log-out';
	import Settings from '@lucide/svelte/icons/settings';
	import { lumia } from '$technical/api/client';

	let { children } = $props();

	let bottomNavEl = $state<HTMLElement | null>(null);

	const authRoutes = ['/login', '/onboarding'];

	const navLinks = [
		{ href: '/articles', label: 'Articles', icon: Newspaper },
		{ href: '/etincelle', label: "L'Étincelle", icon: Sparkles },
		{ href: '/feeds', label: 'Mes flux', icon: Rss },
		{ href: '/a-lire-plus-tard', label: 'À lire', icon: Bookmark }
	];

	function isActive(href: string): boolean {
		return page.url.pathname === href || page.url.pathname.startsWith(`${href}/`);
	}

	const mainPadding = $derived(
		authRoutes.includes(page.url.pathname) ? '' : 'pb-20 sm:pb-6'
	);

	async function logout() {
		await lumia.user.logout();
		await goto('/login');
	}

	onMount(() => {
		if (!bottomNavEl) return;
		const measure = () => {
			if (bottomNavEl) {
				const height = bottomNavEl.getBoundingClientRect().height;
				document.documentElement.style.setProperty('--bottom-nav-h', `${height}px`);
			}
		};
		const observer = new ResizeObserver(measure);
		observer.observe(bottomNavEl);
		window.addEventListener('resize', measure);
		window.addEventListener('orientationchange', measure);
		measure();
		return () => {
			observer.disconnect();
			window.removeEventListener('resize', measure);
			window.removeEventListener('orientationchange', measure);
		};
	});

	onNavigate((navigation) => {
		if (!document.startViewTransition) return;
		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

{#if !authRoutes.includes(page.url.pathname)}
	<header class="sticky top-0 z-30 animate-in border-b bg-card/95 backdrop-blur fade-in slide-in-from-top-2 duration-300">
		<nav class="mx-auto flex max-w-5xl flex-wrap items-center gap-1 px-4 py-3">
			<span class="mr-4 flex items-center gap-1.5 font-serif text-lg font-semibold">
				<Sparkles class="size-5 text-primary transition-transform duration-300 hover:rotate-12" />
				Lumia
			</span>
			<div class="hidden items-center gap-1 sm:flex">
				{#each navLinks as link (link.href)}
					<Button variant={isActive(link.href) ? 'secondary' : 'ghost'} size="sm" href={link.href}>
						<link.icon class="size-4" />
						{link.label}
					</Button>
				{/each}
			</div>
			<div class="ml-auto flex items-center gap-1">
				<Button variant="outline" size="sm" onclick={logout} class="hidden sm:inline-flex">
					<LogOut class="size-4" />
					Déconnexion
				</Button>
			</div>
		</nav>
	</header>
{/if}

{#key page.url.pathname}
	<main
		class="mx-auto max-w-5xl animate-in px-4 py-6 fade-in slide-in-from-bottom-3 duration-500 sm:px-6 {mainPadding}"
	>
		{@render children()}
	</main>
{/key}

{#if !authRoutes.includes(page.url.pathname)}
	<nav
		bind:this={bottomNavEl}
		class="fixed inset-x-0 bottom-0 z-30 flex items-center justify-around border-t bg-card/95 py-1.5 backdrop-blur sm:hidden"
	>
		{#each navLinks as link (link.href)}
			<a
				href={link.href}
				class="flex flex-1 flex-col items-center gap-0.5 rounded-md py-1.5 text-[11px] transition-colors {isActive(
					link.href
				)
					? 'text-primary'
					: 'text-muted-foreground'}"
			>
				<link.icon class="size-5 transition-transform {isActive(link.href) ? '-translate-y-0.5' : ''}" />
				{link.label}
			</a>
		{/each}
		<a
			href="/settings"
			class="flex flex-1 flex-col items-center gap-0.5 rounded-md py-1.5 text-[11px] transition-colors {isActive(
				'/settings'
			)
				? 'text-primary'
				: 'text-muted-foreground'}"
		>
			<Settings
				class="size-5 transition-transform {isActive('/settings') ? '-translate-y-0.5' : ''}"
			/>
			Réglages
		</a>
	</nav>
{/if}
