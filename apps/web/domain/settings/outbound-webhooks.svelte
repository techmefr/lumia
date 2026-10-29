<script lang="ts">
	import { copyToClipboard } from '$technical/browser/copy-to-clipboard';
	import { onMount } from 'svelte';
	import {
		ApiError,
		WEBHOOK_EVENTS,
		type Webhook,
		type WebhookDelivery,
		type WebhookEvent
	} from '@lumia/core';
	import { Button, Card, CardContent, Input, toast } from '@lumia/ui';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte.js';

	const EVENT_LABELS: Record<WebhookEvent, MessageKey> = {
		'article.saved': 'webhooks.event.saved',
		'article.favorited': 'webhooks.event.favorited',
		'playlist.article_added': 'webhooks.event.playlist'
	};

	let webhooks = $state<Webhook[]>([]);
	let url = $state('');
	let selected = $state<WebhookEvent[]>(['article.saved']);
	let saving = $state(false);
	let error = $state<MessageKey | null>(null);
	// Held in memory only: the backend cannot show the secret again once this page is left.
	let secret = $state<string | null>(null);
	let openDeliveries = $state<string | null>(null);
	let deliveries = $state<WebhookDelivery[]>([]);

	async function load() {
		try {
			webhooks = await lumia.webhook.listWebhooks();
		} catch {
			error = 'webhooks.loadFailed';
		}
	}

	function failureOf(cause: unknown): MessageKey {
		if (cause instanceof ApiError && cause.status === 422) return 'webhooks.urlBlocked';
		if (cause instanceof ApiError && cause.status === 409) return 'webhooks.limitReached';
		return 'webhooks.saveFailed';
	}

	async function add(event: SubmitEvent) {
		event.preventDefault();
		if (selected.length === 0) {
			error = 'webhooks.eventsRequired';
			return;
		}
		saving = true;
		error = null;
		try {
			const created = await lumia.webhook.createWebhook({ url: url.trim(), events: selected });
			const { secret: issued, ...webhook } = created;
			webhooks = [...webhooks, webhook];
			secret = issued;
			url = '';
		} catch (cause) {
			error = failureOf(cause);
		} finally {
			saving = false;
		}
	}

	async function toggle(webhook: Webhook) {
		try {
			const updated = await lumia.webhook.updateWebhook(webhook.id, { active: !webhook.active });
			webhooks = webhooks.map((item) => (item.id === updated.id ? updated : item));
		} catch {
			toast(t('webhooks.saveFailed'), { tone: 'destructive' });
		}
	}

	async function remove(webhook: Webhook) {
		try {
			await lumia.webhook.deleteWebhook(webhook.id);
			webhooks = webhooks.filter((item) => item.id !== webhook.id);
			if (openDeliveries === webhook.id) openDeliveries = null;
			toast(t('webhooks.removed'));
		} catch {
			toast(t('webhooks.saveFailed'), { tone: 'destructive' });
		}
	}

	async function toggleDeliveries(webhook: Webhook) {
		if (openDeliveries === webhook.id) {
			openDeliveries = null;
			return;
		}
		try {
			deliveries = await lumia.webhook.listDeliveries(webhook.id);
			openDeliveries = webhook.id;
		} catch {
			toast(t('webhooks.loadFailed'), { tone: 'destructive' });
		}
	}

	async function copySecret() {
		if (!secret) return;
		const copied = await copyToClipboard(secret);
		toast(copied ? t('webhooks.secretCopied') : t('common.copyFailed'), copied ? undefined : { tone: 'destructive' });
	}

	onMount(load);
</script>

<Card data-test-webhooks>
	<CardContent class="flex flex-col gap-4 pt-6">
		<div>
			<h2 class="text-sm font-semibold text-muted-foreground">{t('webhooks.title')}</h2>
			<p class="mt-1 text-xs text-muted-foreground">{t('webhooks.description')}</p>
		</div>

		<form class="flex flex-col gap-3" onsubmit={add}>
			<label class="flex flex-col gap-1 text-sm">
				<span class="font-medium">{t('webhooks.urlLabel')}</span>
				<Input
					data-test-webhook-url
					type="url"
					required
					bind:value={url}
					placeholder="https://"
					maxlength={2048}
				/>
			</label>
			<fieldset class="flex flex-col gap-1.5">
				<legend class="mb-1 text-sm font-medium">{t('webhooks.eventsLegend')}</legend>
				{#each WEBHOOK_EVENTS as webhookEvent (webhookEvent)}
					<label class="flex min-h-8 items-center gap-2 text-sm">
						<input
							data-test-webhook-event={webhookEvent}
							type="checkbox"
							value={webhookEvent}
							bind:group={selected}
							class="size-4"
						/>
						{t(EVENT_LABELS[webhookEvent])}
					</label>
				{/each}
			</fieldset>
			<Button data-test-webhook-submit type="submit" disabled={saving} class="w-fit"
				>{saving ? t('common.adding') : t('webhooks.add')}</Button
			>
		</form>

		{#if error}
			<p data-test-webhooks-error role="alert" class="text-sm text-destructive">{t(error)}</p>
		{/if}

		{#if secret}
			<div data-test-webhook-secret-card role="status" class="flex flex-col gap-2 text-sm">
				<label class="flex flex-col gap-1">
					<span class="text-xs font-medium">{t('webhooks.secretLabel')}</span>
					<input
						data-test-webhook-secret
						type="text"
						readonly
						value={secret}
						onfocus={(event) => event.currentTarget.select()}
						class="h-9 rounded-md border border-input bg-background px-2 text-xs"
					/>
				</label>
				<p class="text-xs text-muted-foreground">{t('webhooks.secretNote')}</p>
				<Button data-test-webhook-copy type="button" variant="outline" class="w-fit" onclick={copySecret}
					>{t('webhooks.copySecret')}</Button
				>
			</div>
		{/if}

		{#if webhooks.length === 0}
			<p data-test-webhooks-empty class="text-xs text-muted-foreground">{t('webhooks.empty')}</p>
		{:else}
			<ul class="flex flex-col gap-3">
				{#each webhooks as webhook (webhook.id)}
					<li data-test-webhook={webhook.id} class="flex flex-col gap-2 rounded-md border p-3">
						<p class="text-sm font-medium break-all">
							{webhook.url}
							{#if !webhook.active}
								<span data-test-webhook-paused class="ms-2 text-xs font-normal text-muted-foreground"
									>({t('webhooks.paused')})</span
								>
							{/if}
						</p>
						<p class="text-xs text-muted-foreground">
							{webhook.events.map((webhookEvent) => t(EVENT_LABELS[webhookEvent])).join(', ')}
						</p>
						<div class="flex flex-wrap gap-2">
							<Button
								data-test-webhook-toggle
								type="button"
								variant="outline"
								size="sm"
								onclick={() => toggle(webhook)}
								>{webhook.active ? t('webhooks.pause') : t('webhooks.resume')}</Button
							>
							<Button
								data-test-webhook-history
								type="button"
								variant="outline"
								size="sm"
								aria-expanded={openDeliveries === webhook.id}
								aria-controls="deliveries-{webhook.id}"
								onclick={() => toggleDeliveries(webhook)}>{t('webhooks.deliveries')}</Button
							>
							<Button
								data-test-webhook-remove
								type="button"
								variant="outline"
								size="sm"
								onclick={() => remove(webhook)}>{t('webhooks.remove')}</Button
							>
						</div>
						<div id="deliveries-{webhook.id}" hidden={openDeliveries !== webhook.id}>
							{#if openDeliveries === webhook.id}
								{#if deliveries.length === 0}
									<p data-test-deliveries-empty class="text-xs text-muted-foreground">
										{t('webhooks.noDeliveries')}
									</p>
								{:else}
									<ul class="flex flex-col gap-1 text-xs">
										{#each deliveries as delivery (delivery.id)}
											<li data-test-delivery={delivery.status}>
												<span class="font-medium">{t(`webhooks.status.${delivery.status}`)}</span>
												· {t(EVENT_LABELS[delivery.event])} · {t('webhooks.attempts', {
													count: delivery.attempts
												})}
												{#if delivery.last_error}
													· <span class="text-destructive">{delivery.last_error}</span>
												{/if}
											</li>
										{/each}
									</ul>
								{/if}
							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</CardContent>
</Card>
