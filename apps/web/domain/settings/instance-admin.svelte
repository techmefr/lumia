<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, CardContent, Input, Label, toast } from '@lumia/ui';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import type {
		AccessMode,
		AccessRequest,
		AccountUsage,
		InstanceSettings,
		Role
	} from '@lumia/core';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	const ACCESS_MODES = $derived<{ value: AccessMode; label: string }[]>([
		{ value: 'closed', label: t('admin.modeClosed') },
		{ value: 'on_approval', label: t('admin.modeOnApproval') },
		{ value: 'open', label: t('admin.modeOpen') }
	]);

	let settings = $state<InstanceSettings | null>(null);
	let accounts = $state<AccountUsage[]>([]);
	let requests = $state<AccessRequest[]>([]);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let maxAccounts = $state(0);
	let accountQuotaMb = $state(0);
	let accessMode = $state<AccessMode>('closed');

	function roleLabel(role: Role): string {
		return role === 'admin' ? t('admin.roleAdmin') : t('admin.roleMember');
	}

	function hydrate(next: InstanceSettings) {
		settings = next;
		maxAccounts = next.max_accounts;
		accountQuotaMb = next.disk_quota_mb;
		accessMode = next.access_mode;
	}

	async function load() {
		loading = true;
		error = null;
		try {
			const [instanceSettings, accountList, requestList] = await Promise.all([
				lumia.instance.getSettings(),
				lumia.instance.listAccounts(),
				lumia.instance.listAccessRequests('pending')
			]);
			hydrate(instanceSettings);
			accounts = accountList;
			requests = requestList;
		} catch {
			settings = null;
			error = t('admin.unavailable');
		} finally {
			loading = false;
		}
	}

	async function save() {
		saving = true;
		error = null;
		try {
			hydrate(
				await lumia.instance.updateSettings({
					max_accounts: maxAccounts,
					disk_quota_mb: accountQuotaMb,
					access_mode: accessMode
				})
			);
			toast(t('admin.saved'));
		} catch {
			error = t('admin.saveFailed');
		} finally {
			saving = false;
		}
	}

	async function decide(request: AccessRequest, approved: boolean) {
		saving = true;
		error = null;
		try {
			if (approved) await lumia.instance.approveAccessRequest(request.id);
			else await lumia.instance.rejectAccessRequest(request.id);
			await load();
		} catch {
			error = t('admin.decideFailed');
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		void load();
	});
</script>

<Card>
	<CardContent class="flex flex-col gap-6 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-lg font-semibold">
				<ShieldCheck class="size-5 text-primary" />
				{t('admin.title')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">{t('admin.intro')}</p>
		</div>

		{#if loading}
			<p data-test-admin-loading class="text-sm text-muted-foreground" aria-live="polite">
				{t('admin.loading')}
			</p>
		{:else if settings === null}
			<p data-test-admin-unavailable class="text-sm text-destructive" aria-live="polite">
				{error ?? t('admin.unavailable')}
			</p>
		{:else}
			<div data-test-admin-panel class="flex flex-col gap-6">
				<div class="grid gap-4 sm:grid-cols-2">
					<div class="flex flex-col gap-2">
						<Label for="admin-max-accounts">{t('admin.maxAccounts')}</Label>
						<Input
							id="admin-max-accounts"
							data-test-max-accounts
							type="number"
							min="1"
							bind:value={maxAccounts}
							aria-describedby="admin-max-accounts-hint"
						/>
						<p id="admin-max-accounts-hint" class="text-xs text-muted-foreground">
							{t('admin.accountCount', { count: String(settings.account_count) })}
						</p>
					</div>

					<div class="flex flex-col gap-2">
						<Label for="admin-account-quota">{t('admin.accountQuota')}</Label>
						<Input
							id="admin-account-quota"
							data-test-account-quota
							type="number"
							min="1"
							bind:value={accountQuotaMb}
						/>
					</div>
				</div>

				<div class="flex flex-col gap-2">
					<Label for="admin-access-mode">{t('admin.accessMode')}</Label>
					<select
						id="admin-access-mode"
						data-test-access-mode
						bind:value={accessMode}
						class="h-10 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
					>
						{#each ACCESS_MODES as option (option.value)}
							<option value={option.value}>{option.label}</option>
						{/each}
					</select>
				</div>

				{#if error}
					<p data-test-admin-error class="text-sm text-destructive" aria-live="polite">{error}</p>
				{/if}

				<Button data-test-admin-save class="self-start" disabled={saving} onclick={save}>
					{saving ? t('common.saving') : t('common.save')}
				</Button>

				<section class="flex flex-col gap-2 border-t pt-4">
					<h3 class="text-sm font-semibold text-muted-foreground">{t('admin.accounts')}</h3>
					<div class="overflow-x-auto">
						<table class="w-full text-left text-sm">
							<caption class="sr-only">{t('admin.accounts')}</caption>
							<thead>
								<tr class="text-xs text-muted-foreground">
									<th scope="col" class="py-1">{t('admin.account')}</th>
									<th scope="col" class="py-1">{t('admin.role')}</th>
									<th scope="col" class="py-1">{t('admin.usage')}</th>
								</tr>
							</thead>
							<tbody>
								{#each accounts as account (account.id)}
									<tr data-test-account-row class="border-t">
										<td class="py-2">{account.email}</td>
										<td class="py-2">{roleLabel(account.role)}</td>
										<td class="py-2">{account.used_mb} / {account.quota_mb} Mo</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</section>

				<section class="flex flex-col gap-2 border-t pt-4">
					<h3 class="text-sm font-semibold text-muted-foreground">{t('admin.requests')}</h3>
					{#if requests.length === 0}
						<p data-test-no-requests class="text-xs text-muted-foreground">
							{t('admin.noRequests')}
						</p>
					{:else}
						<ul class="flex flex-col gap-2">
							{#each requests as request (request.id)}
								<li
									data-test-access-request
									class="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3"
								>
									<span class="text-sm">{request.username} — {request.email}</span>
									<span class="flex gap-2">
										<Button
											data-test-approve-request
											size="sm"
											disabled={saving}
											onclick={() => decide(request, true)}
										>
											{t('admin.approve')}
										</Button>
										<Button
											data-test-reject-request
											variant="outline"
											size="sm"
											disabled={saving}
											onclick={() => decide(request, false)}
										>
											{t('admin.reject')}
										</Button>
									</span>
								</li>
							{/each}
						</ul>
					{/if}
				</section>
			</div>
		{/if}
	</CardContent>
</Card>
