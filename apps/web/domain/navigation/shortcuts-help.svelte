<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$app/paths';
	import { Button } from '@lumia/ui';
	import X from '@lucide/svelte/icons/x';
	import {
		HELP_SHORTCUTS,
		NAVIGATION_SHORTCUTS,
		READING_SHORTCUTS,
		type ShortcutEntry
	} from '$technical/keyboard/shortcut-catalogue';
	import { t } from '$technical/i18n/i18n.svelte.js';

	interface Props {
		onClose: () => void;
	}

	let { onClose }: Props = $props();

	let dialogEl = $state<HTMLElement>();

	const sections = $derived([
		{ id: 'navigation', title: t('shortcuts.navigation'), entries: NAVIGATION_SHORTCUTS },
		{ id: 'reading', title: t('shortcuts.reading'), entries: READING_SHORTCUTS },
		{ id: 'general', title: t('shortcuts.general'), entries: HELP_SHORTCUTS }
	]);

	function focusableElements(): HTMLElement[] {
		if (!dialogEl) return [];
		return Array.from(
			dialogEl.querySelectorAll<HTMLElement>(
				'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
			)
		);
	}

	function trapTab(event: KeyboardEvent) {
		const focusable = focusableElements();
		if (focusable.length === 0) return;
		const first = focusable[0];
		const last = focusable[focusable.length - 1];
		if (event.shiftKey && document.activeElement === first) {
			event.preventDefault();
			last.focus();
		} else if (!event.shiftKey && document.activeElement === last) {
			event.preventDefault();
			first.focus();
		}
	}

	function onKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			event.preventDefault();
			onClose();
			return;
		}
		if (event.key === 'Tab') trapTab(event);
	}

	function labelOf(entry: ShortcutEntry): string {
		return t(entry.labelKey);
	}

	onMount(() => {
		const previouslyFocused = document.activeElement as HTMLElement | null;
		focusableElements()[0]?.focus();
		return () => previouslyFocused?.focus();
	});
</script>

<svelte:window onkeydown={onKeydown} />

<div
	bind:this={dialogEl}
	data-test-shortcuts-help
	role="dialog"
	aria-modal="true"
	aria-label={t('shortcuts.title')}
	class="fixed inset-0 z-50 flex items-center justify-center bg-background/90 p-4 backdrop-blur"
>
	<div
		class="flex max-h-full w-full max-w-lg animate-in flex-col gap-4 overflow-y-auto rounded-2xl border bg-card p-5 shadow-xl fade-in zoom-in-95 duration-200"
	>
		<div class="flex items-start justify-between gap-3">
			<h2 class="font-serif text-xl font-semibold">{t('shortcuts.title')}</h2>
			<Button
				data-test-shortcuts-help-close
				variant="ghost"
				size="sm"
				aria-label={t('common.close')}
				onclick={onClose}
			>
				<X class="size-4" />
			</Button>
		</div>

		{#each sections as section (section.id)}
			<section class="flex flex-col gap-1.5">
				<h3 class="text-sm font-semibold text-muted-foreground">{section.title}</h3>
				<dl class="flex flex-col gap-1">
					{#each section.entries as entry (entry.id)}
						<div class="flex items-baseline justify-between gap-4 text-sm">
							<dt class="flex items-center gap-1">
								{#each entry.keys as key (key)}
									<kbd>{key}</kbd>
								{/each}
							</dt>
							<dd class="text-right text-muted-foreground">{labelOf(entry)}</dd>
						</div>
					{/each}
				</dl>
			</section>
		{/each}

		<p class="border-t pt-3 text-xs text-muted-foreground">
			{t('shortcuts.offHint')}
			<a class="underline" href="{base}/settings">{t('nav.settings')}</a>
		</p>
	</div>
</div>
