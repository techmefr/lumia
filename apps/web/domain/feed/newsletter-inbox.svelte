<script lang="ts">
	import { copyToClipboard } from '$technical/browser/copy-to-clipboard';
	import { onMount } from 'svelte';
	import { base } from '$technical/paths/base';
	import type { NewsletterInboxStatus } from '@lumia/core';
	import { Card, CardContent, CardDescription, CardHeader, CardTitle, toast } from '@lumia/ui';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';

	let status = $state<NewsletterInboxStatus | null>(null);
	let pending = $state(false);
	let failure = $state<MessageKey | null>(null);
	// Held in memory only: the backend keeps a hash, so once the page is left the address is gone.
	let address = $state<string | null>(null);

	onMount(async () => {
		try {
			status = await lumia.newsletter.getInboxStatus();
		} catch {
			failure = 'newsletters.failed';
		}
	});

	async function create() {
		pending = true;
		failure = null;
		try {
			const created = await lumia.newsletter.createInbox();
			address = `${window.location.origin}${base}/api/inbound/newsletters/${created.token}`;
			status = { active: true, created_at: created.created_at };
		} catch {
			failure = 'newsletters.failed';
		} finally {
			pending = false;
		}
	}

	async function revoke() {
		pending = true;
		failure = null;
		try {
			await lumia.newsletter.revokeInbox();
			address = null;
			status = { active: false, created_at: null };
			toast(t('newsletters.revoked'));
		} catch {
			failure = 'newsletters.failed';
		} finally {
			pending = false;
		}
	}

	async function copy() {
		if (!address) return;
		const copied = await copyToClipboard(address);
		toast(copied ? t('newsletters.copied') : t('common.copyFailed'), copied ? undefined : { tone: 'destructive' });
	}
</script>

<Card class="magic-bento-cell" data-test-newsletters>
	<CardHeader>
		<CardTitle>{t('newsletters.title')}</CardTitle>
		<CardDescription>{t('newsletters.description')}</CardDescription>
	</CardHeader>
	<CardContent class="flex flex-col gap-3 text-sm">
		{#if address}
			<label class="flex flex-col gap-1">
				<span class="text-xs font-medium">{t('newsletters.addressLabel')}</span>
				<input
					data-test-newsletters-address
					type="text"
					readonly
					value={address}
					onfocus={(event) => event.currentTarget.select()}
					class="h-9 rounded-md border border-input bg-background px-2 text-xs"
				/>
			</label>
			<p class="text-muted-foreground">{t('newsletters.usage')}</p>
			<button
				type="button"
				onclick={copy}
				data-test-newsletters-copy
				class="w-fit rounded-md border px-3 py-1.5 text-xs hover:bg-secondary"
			>
				{t('newsletters.copy')}
			</button>
		{:else if status?.active}
			<p data-test-newsletters-active class="text-muted-foreground">{t('newsletters.active')}</p>
		{/if}

		<div class="flex flex-wrap gap-2">
			<button
				type="button"
				onclick={create}
				disabled={pending || status === null}
				data-test-newsletters-create
				class="rounded-md border px-3 py-1.5 text-xs hover:bg-secondary disabled:opacity-50"
			>
				{t(status?.active ? 'newsletters.replace' : 'newsletters.create')}
			</button>
			{#if status?.active}
				<button
					type="button"
					onclick={revoke}
					disabled={pending}
					data-test-newsletters-revoke
					class="rounded-md border border-destructive px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 disabled:opacity-50"
				>
					{t('newsletters.revoke')}
				</button>
			{/if}
		</div>

		{#if failure}
			<p data-test-newsletters-error role="alert" class="text-destructive">{t(failure)}</p>
		{/if}
	</CardContent>
</Card>
