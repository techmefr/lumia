<script lang="ts">
	import { base } from '$app/paths';
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { onMount } from 'svelte';
	import { fade, fly } from 'svelte/transition';
	import { goto, onNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { Button, ClickSpark, Toaster } from '@lumia/ui';
	import Newspaper from '@lucide/svelte/icons/newspaper';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import Rss from '@lucide/svelte/icons/rss';
	import Bookmark from '@lucide/svelte/icons/bookmark';
	import ListMusic from '@lucide/svelte/icons/list-music';
	import Settings from '@lucide/svelte/icons/settings';
	import { isDemo, lumia } from '$technical/api/client';
	import SettingsMenu from '$domain/navigation/settings-menu.svelte';
	import DemoBanner from '$domain/navigation/demo-banner.svelte';
	import { watchUnread } from '$technical/notifications/notification-store.svelte.js';
	import { initLocale, t } from '$technical/i18n/i18n.svelte.js';

	let { children } = $props();

	let bottomNavEl = $state<HTMLElement | null>(null);

	const authRoutes = ['/login', '/onboarding'];

	function isAuthRoute(pathname: string): boolean {
		return authRoutes.some((route) => pathname === base + route);
	}

	// Derived rather than a constant: the labels have to follow a language change.
	const navLinks = $derived([
		{ href: '/articles', label: t('nav.articles'), icon: Newspaper },
		{ href: '/etincelle', label: t('nav.etincelle'), icon: Sparkles },
		{ href: '/feeds', label: t('nav.feeds'), icon: Rss },
		{ href: '/a-lire-plus-tard', label: t('nav.readLater'), icon: Bookmark },
		{ href: '/playlists', label: t('nav.playlists'), icon: ListMusic }
	]);

	// `page.url.pathname` carries the base path, so the comparison has to carry it too.
	function isActive(href: string): boolean {
		const full = base + href;
		return page.url.pathname === full || page.url.pathname.startsWith(`${full}/`);
	}

	const mainPadding = $derived(isAuthRoute(page.url.pathname) ? '' : 'pb-20 sm:pb-6');

	async function logout() {
		await lumia.user.logout();
		await goto(base + '/login');
	}

	const settingsEntries = $derived([
		{ label: t('nav.settings'), href: `${base}/settings` },
		{ label: t('nav.favorites'), href: `${base}/favoris` },
		{ label: t('nav.playlists'), href: `${base}/playlists` },
		{ label: t('nav.logout'), run: logout }
	]);

	onMount(() => {
		initLocale();
		// Owned by the layout so a single poll covers every screen, and it stops with the app.
		return watchUnread(async () => (await lumia.feed.getUnreadCounts()).total);
	});

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
			const transition = document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
			// A guard that redirects starts a second navigation, which aborts this transition.
			// That rejection is expected; unhandled it surfaces as an uncaught InvalidStateError.
			void transition.ready.catch(() => {});
			void transition.finished.catch(() => {});
		});
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<ClickSpark sparkColor="var(--primary)" sparkCount={6} sparkRadius={14} sparkSize={7} duration={320}>

{#if isDemo}
	<DemoBanner />
{/if}

{#if !isAuthRoute(page.url.pathname)}
	<a href="#main-content" class="skip-link">{t('nav.skipToContent')}</a>
	<header class="sticky top-0 z-30 animate-in border-b bg-card/95 backdrop-blur fade-in slide-in-from-top-2 duration-300">
		<nav aria-label={t('nav.main')} class="mx-auto flex max-w-5xl flex-wrap items-center gap-1 px-4 py-3">
			<a href="{base}/articles" class="mr-4 flex items-center gap-1.5 font-serif text-lg font-semibold">
				<Sparkles class="size-5 text-primary transition-transform duration-300 hover:rotate-12" />
				Lumia
			</a>
			<div class="hidden items-center gap-1 sm:flex">
				{#each navLinks as link (link.href)}
					<Button
						variant={isActive(link.href) ? 'secondary' : 'ghost'}
						size="sm"
						href={base + link.href}
						aria-current={isActive(link.href) ? 'page' : undefined}
					>
						<link.icon class="size-4" />
						{link.label}
					</Button>
				{/each}
			</div>
			<div class="ml-auto flex items-center">
				<SettingsMenu
					href="{base}/settings"
					label={t('nav.settings')}
					icon={Settings}
					entries={settingsEntries}
				/>
			</div>
		</nav>
	</header>
{/if}

{#key page.url.pathname}
	<main
		id="main-content"
		class="mx-auto max-w-5xl px-4 py-6 sm:px-6 {mainPadding}"
		in:fly={{ y: 16, duration: 260, delay: 120 }}
		out:fade={{ duration: 120 }}
	>
		{@render children()}
	</main>
{/key}

{#if !isAuthRoute(page.url.pathname)}
	<nav
		bind:this={bottomNavEl}
		aria-label={t('nav.mobile')}
		class="fixed inset-x-0 bottom-0 z-30 flex items-center justify-around border-t bg-card/95 py-1.5 backdrop-blur sm:hidden"
	>
		{#each navLinks as link (link.href)}
			<a
				href={base + link.href}
				aria-current={isActive(link.href) ? 'page' : undefined}
				class="flex min-h-11 flex-1 flex-col items-center gap-0.5 rounded-md py-1.5 text-[11px] transition-colors {isActive(
					link.href
				)
					? 'font-semibold text-primary'
					: 'text-muted-foreground'}"
			>
				<link.icon class="size-5 transition-transform {isActive(link.href) ? '-translate-y-0.5' : ''}" />
				{link.label}
			</a>
		{/each}
	</nav>
{/if}

<Toaster closeLabel={t('common.dismissNotification')} />

</ClickSpark>
