<script lang="ts">
	import { copyToClipboard } from '$technical/browser/copy-to-clipboard';
	import { formatDateInUserTimezone } from '$technical/time/format-date';
	import { getLocale } from '$technical/i18n/i18n.svelte';
	import { onMount } from 'svelte';
	import type { FeverKeyCreated, FeverKeyStatus } from '@lumia/core';
	import { Button, Card, CardContent, Input, Label, toast } from '@lumia/ui';
	import Rss from '@lucide/svelte/icons/rss';
	import { isDemo, lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let status = $state<FeverKeyStatus>({ enabled: false, created_at: null });
	let created = $state<FeverKeyCreated | null>(null);
	let busy = $state(false);
	let error = $state<string | null>(null);

	const endpoint = $derived.by(() => {
		const base = import.meta.env.VITE_API_BASE_URL || window.location.origin;
		return `${String(base).replace(/\/$/, '')}/fever/`;
	});
	const since = $derived(
		status.created_at ? formatDateInUserTimezone(status.created_at, getLocale(), { dateStyle: 'medium' }) : ''
	);

	const fields = $derived(
		created
			? [
					{ id: 'fever-endpoint', test: 'endpoint', label: t('fever.endpointLabel'), value: endpoint },
					{ id: 'fever-username', test: 'username', label: t('fever.usernameLabel'), value: created.email },
					{ id: 'fever-password', test: 'secret', label: t('fever.passwordLabel'), value: created.secret }
				]
			: []
	);

	async function refresh() {
		status = await lumia.user.getFeverKey();
	}

	async function createKey() {
		busy = true;
		error = null;
		try {
			created = await lumia.user.createFeverKey();
			await refresh();
		} catch {
			error = t('fever.failed');
		} finally {
			busy = false;
		}
	}

	async function revokeKey() {
		busy = true;
		error = null;
		try {
			await lumia.user.revokeFeverKey();
			created = null;
			await refresh();
			toast(t('fever.revoked'));
		} catch {
			error = t('fever.failed');
		} finally {
			busy = false;
		}
	}

	function copy(value: string) {
		void copyToClipboard(value).then((copied) => {
			toast(copied ? t('fever.copied') : t('common.copyFailed'), copied ? undefined : { tone: 'destructive' });
		});
	}

	onMount(() => {
		if (isDemo) return;
		void refresh().catch(() => {
			status = { enabled: false, created_at: null };
		});
	});
</script>

{#if !isDemo}
	<Card data-test-fever-card>
		<CardContent class="flex flex-col gap-6 pt-6">
			<div>
				<h2 class="flex items-center gap-2 text-lg font-semibold">
					<Rss class="size-5 text-primary" aria-hidden="true" />
					{t('fever.title')}
				</h2>
				<p class="mt-1 text-sm text-muted-foreground">{t('fever.intro')}</p>
			</div>

			{#if created}
				<div data-test-fever-credentials class="flex flex-col gap-3">
					<p role="alert" class="text-sm font-medium text-destructive">
						{t('fever.secretWarning')}
					</p>
					{#each fields as field (field.id)}
						<div class="flex flex-col gap-1.5">
							<Label for={field.id}>{field.label}</Label>
							<div class="flex gap-2">
								<Input
									id={field.id}
									data-test-fever-field={field.test}
									readonly
									class="font-mono"
									value={field.value}
								/>
								<Button variant="outline" type="button" onclick={() => copy(field.value)}>
									{t('fever.copy')}
									<span class="sr-only">: {field.label}</span>
								</Button>
							</div>
						</div>
					{/each}
					<p class="text-xs text-muted-foreground">{t('fever.hint')}</p>
					<Button
						data-test-fever-done
						class="self-start"
						onclick={() => {
							created = null;
						}}
					>
						{t('fever.done')}
					</Button>
				</div>
			{:else if status.enabled}
				<div class="flex flex-col gap-3">
					<p data-test-fever-status class="text-sm font-medium">
						{t('fever.statusOn', { date: since })}
					</p>
					{#if error}
						<p data-test-fever-error role="alert" class="text-sm text-destructive">{error}</p>
					{/if}
					<div class="flex flex-wrap gap-2">
						<Button data-test-fever-create variant="outline" disabled={busy} onclick={createKey}>
							{busy ? t('fever.working') : t('fever.regenerate')}
						</Button>
						<Button data-test-fever-revoke variant="ghost" disabled={busy} onclick={revokeKey}>
							{t('fever.revoke')}
						</Button>
					</div>
				</div>
			{:else}
				<div class="flex flex-col gap-3">
					<p data-test-fever-status class="text-sm text-muted-foreground">
						{t('fever.statusOff')}
					</p>
					{#if error}
						<p data-test-fever-error role="alert" class="text-sm text-destructive">{error}</p>
					{/if}
					<Button
						data-test-fever-create
						class="self-start"
						disabled={busy}
						onclick={createKey}
					>
						{busy ? t('fever.working') : t('fever.enable')}
					</Button>
				</div>
			{/if}
		</CardContent>
	</Card>
{/if}
