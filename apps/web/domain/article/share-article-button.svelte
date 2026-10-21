<script lang="ts">
	import { base } from '$app/paths';
	import { ApiError, type ArticleShareStatus } from '@lumia/core';
	import { toast } from '@lumia/ui';
	import Link2 from '@lucide/svelte/icons/link-2';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';

	interface Props {
		articleId: string;
	}

	const { articleId }: Props = $props();

	let open = $state(false);
	let status = $state<ArticleShareStatus | null>(null);
	let loading = $state(false);
	let pending = $state(false);
	let failure = $state<MessageKey | null>(null);
	// Held in memory only: the backend keeps a hash, so once the panel is closed the link is gone.
	let link = $state<string | null>(null);

	async function toggle() {
		open = !open;
		if (!open || status !== null) return;
		loading = true;
		failure = null;
		try {
			status = await lumia.article.getShareStatus(articleId);
		} catch {
			failure = 'share.failed';
		} finally {
			loading = false;
		}
	}

	async function create() {
		pending = true;
		failure = null;
		try {
			const created = await lumia.article.createShare(articleId);
			link = `${window.location.origin}${base}/share/${created.token}`;
			status = { enabled: true, shared: true, created_at: created.created_at };
		} catch (error) {
			const refused = error instanceof ApiError && error.status === 403;
			if (refused && status) status = { ...status, enabled: false };
			failure = 'share.failed';
		} finally {
			pending = false;
		}
	}

	async function revoke() {
		pending = true;
		failure = null;
		try {
			await lumia.article.revokeShare(articleId);
			link = null;
			status = status ? { ...status, shared: false, created_at: null } : status;
			toast(t('share.revoked'));
		} catch {
			failure = 'share.failed';
		} finally {
			pending = false;
		}
	}

	async function copy() {
		if (!link) return;
		await navigator.clipboard.writeText(link);
		toast(t('share.copied'));
	}
</script>

<div class="relative print:hidden" data-test-share>
	<button
		type="button"
		onclick={toggle}
		aria-expanded={open}
		aria-controls="share-panel-{articleId}"
		data-test-share-toggle
		class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
	>
		<Link2 class="size-4" aria-hidden="true" />
		{t('share.open')}
	</button>

	{#if open}
		<div
			id="share-panel-{articleId}"
			role="group"
			aria-label={t('share.title')}
			data-test-share-panel
			class="absolute right-0 z-40 mt-1 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-3 rounded-lg border bg-card p-4 text-sm shadow-lg"
		>
			{#if loading}
				<p data-test-share-loading role="status">{t('share.loading')}</p>
			{:else if status && !status.enabled}
				<p data-test-share-disabled>{t('share.disabled')}</p>
			{:else if status}
				<p class="text-muted-foreground">{t('share.intro')}</p>

				{#if link}
					<label class="flex flex-col gap-1">
						<span class="text-xs font-medium">{t('share.linkLabel')}</span>
						<input
							data-test-share-link
							type="text"
							readonly
							value={link}
							onfocus={(event) => event.currentTarget.select()}
							class="h-9 rounded-md border border-input bg-background px-2 text-xs"
						/>
					</label>
					<button
						type="button"
						onclick={copy}
						data-test-share-copy
						class="w-fit rounded-md border px-3 py-1.5 text-xs hover:bg-secondary"
					>
						{t('share.copy')}
					</button>
				{:else if status.shared}
					<p data-test-share-active class="text-muted-foreground">{t('share.active')}</p>
				{/if}

				<p class="text-xs text-muted-foreground">{t('share.noindexNote')}</p>

				<div class="flex flex-wrap gap-2">
					<button
						type="button"
						onclick={create}
						disabled={pending}
						data-test-share-create
						class="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground disabled:opacity-60"
					>
						{status.shared ? t('share.replace') : t('share.create')}
					</button>
					{#if status.shared}
						<button
							type="button"
							onclick={revoke}
							disabled={pending}
							data-test-share-revoke
							class="rounded-md border px-3 py-1.5 text-xs hover:bg-secondary disabled:opacity-60"
						>
							{t('share.revoke')}
						</button>
					{/if}
				</div>
			{/if}

			{#if failure}
				<p data-test-share-error role="alert" class="text-xs text-destructive">{t(failure)}</p>
			{/if}
		</div>
	{/if}
</div>
