<script lang="ts">
	import { base } from '$technical/paths/base';
	import { onMount } from 'svelte';
	import { Notification01Icon } from '@hugeicons/core-free-icons';
	import { Icon } from '@lumia/ui';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte';

	const POLL_MS = 120_000;

	let unread = $state(0);

	async function refresh() {
		try {
			unread = (await lumia.savedSearch.listNotifications(1, 0)).unread_count;
		} catch {
			// A badge is decoration: logged out or offline just leaves it as it was.
		}
	}

	onMount(() => {
		void refresh();
		const timer = setInterval(refresh, POLL_MS);
		return () => clearInterval(timer);
	});
</script>

<a
	data-test-alert-bell
	href="{base}/alerts"
	aria-label={t('alerts.bell', { count: unread })}
	class="relative mr-1 flex min-h-9 min-w-9 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
>
	<Icon icon={Notification01Icon} class="size-5" />
	{#if unread > 0}
		<span
			data-test-alert-badge
			aria-hidden="true"
			class="absolute -right-0.5 -top-0.5 flex min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold text-primary-foreground"
		>
			{unread > 99 ? '99+' : unread}
		</span>
	{/if}
</a>
