<script lang="ts">
	import { onMount } from 'svelte';
	import QRCode from 'qrcode';
	import { ApiError, secondFactorFailure, type Me, type TotpEnrolment } from '@lumia/core';
	import { Button, Card, CardContent, Input, Label, toast } from '@lumia/ui';
	import ShieldCheck from '@lucide/svelte/icons/shield-check';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	/** Below this, a reader is one lost phone away from being locked out for good. */
	const LOW_RECOVERY_CODES = 3;

	type Step = 'idle' | 'enrolling' | 'showing-codes' | 'disabling' | 'renewing';

	let me = $state<Me | null>(null);
	let step = $state<Step>('idle');
	let enrolment = $state<TotpEnrolment | null>(null);
	let qrDataUrl = $state<string | null>(null);
	let recoveryCodes = $state<string[]>([]);
	let code = $state('');
	let password = $state('');
	let busy = $state(false);
	let error = $state<string | null>(null);

	const isEnabled = $derived(me?.totp_enabled ?? false);
	const codesLeft = $derived(me?.recovery_codes_left ?? 0);
	// An account that only ever came in through SSO or a magic link has no password to re-prove
	// itself with, so the authenticator it is about to give up is what it is asked for instead.
	const disableWithPassword = $derived(me?.password_set ?? true);

	function reset() {
		step = 'idle';
		enrolment = null;
		qrDataUrl = null;
		code = '';
		password = '';
		error = null;
	}

	function messageFor(err: unknown): string {
		if (secondFactorFailure(err) !== null) return t('totp.invalidCode');
		if (err instanceof ApiError && err.status === 401) return t('totp.wrongPassword');
		return t('totp.failed');
	}

	async function refreshMe() {
		me = await lumia.user.getMe();
	}

	async function startEnrolment() {
		busy = true;
		error = null;
		try {
			enrolment = await lumia.user.startTotpEnrolment();
			qrDataUrl = await QRCode.toDataURL(enrolment.otpauth_uri, { margin: 1, width: 220 });
			step = 'enrolling';
		} catch (err) {
			error = messageFor(err);
		} finally {
			busy = false;
		}
	}

	async function confirmEnrolment(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = null;
		try {
			recoveryCodes = await lumia.user.confirmTotpEnrolment(code.trim());
			await refreshMe();
			code = '';
			step = 'showing-codes';
		} catch (err) {
			error = messageFor(err);
		} finally {
			busy = false;
		}
	}

	async function renew(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = null;
		try {
			recoveryCodes = await lumia.user.renewRecoveryCodes(code.trim());
			await refreshMe();
			code = '';
			step = 'showing-codes';
		} catch (err) {
			error = messageFor(err);
		} finally {
			busy = false;
		}
	}

	async function disable(event: SubmitEvent) {
		event.preventDefault();
		busy = true;
		error = null;
		try {
			await lumia.user.disableTotp(
				disableWithPassword ? password : null,
				disableWithPassword ? {} : { totp_code: code.trim() }
			);
			await refreshMe();
			reset();
			toast(t('totp.disabled'));
		} catch (err) {
			error = messageFor(err);
		} finally {
			busy = false;
		}
	}

	function copyRecoveryCodes() {
		void navigator.clipboard.writeText(recoveryCodes.join('\n')).then(() => {
			toast(t('totp.copied'));
		});
	}

	function acknowledgeRecoveryCodes() {
		recoveryCodes = [];
		reset();
		toast(t('totp.enabled'));
	}

	onMount(() => {
		void refreshMe().catch(() => {
			me = null;
		});
	});
</script>

<Card>
	<CardContent class="flex flex-col gap-6 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-lg font-semibold">
				<ShieldCheck class="size-5 text-primary" />
				{t('totp.title')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">{t('totp.intro')}</p>
		</div>

		{#if step === 'showing-codes'}
			<div data-test-recovery-codes class="flex flex-col gap-3">
				<h3 class="text-sm font-semibold">{t('totp.recoveryTitle')}</h3>
				<p class="text-sm text-muted-foreground">{t('totp.recoveryIntro')}</p>
				<p role="alert" class="text-sm font-medium text-destructive">
					{t('totp.recoveryWarning')}
				</p>
				<ul class="grid gap-1 rounded-lg border bg-muted/30 p-4 font-mono text-sm sm:grid-cols-2">
					{#each recoveryCodes as recoveryCode (recoveryCode)}
						<li>{recoveryCode}</li>
					{/each}
				</ul>
				<div class="flex flex-wrap gap-2">
					<Button variant="outline" onclick={copyRecoveryCodes}>{t('totp.copy')}</Button>
					<Button data-test-recovery-done onclick={acknowledgeRecoveryCodes}>
						{t('totp.recoveryDone')}
					</Button>
				</div>
			</div>
		{:else if step === 'enrolling' && enrolment}
			<div class="flex flex-col gap-4">
				<p class="text-sm text-muted-foreground">{t('totp.scanHint')}</p>
				{#if qrDataUrl}
					<img
						data-test-totp-qr
						src={qrDataUrl}
						alt={t('totp.qrAlt')}
						class="size-[220px] self-start rounded-lg border bg-white p-2"
					/>
				{/if}
				<div class="flex flex-col gap-1">
					<span class="text-sm font-medium">{t('totp.secretLabel')}</span>
					<code data-test-totp-secret class="rounded bg-muted px-2 py-1 font-mono text-sm break-all">
						{enrolment.secret}
					</code>
					<p class="text-xs text-muted-foreground">{t('totp.secretHint')}</p>
				</div>
				<form data-test-totp-confirm-form class="flex flex-col gap-3" onsubmit={confirmEnrolment}>
					<div class="flex flex-col gap-1.5">
						<Label for="totp-code">{t('totp.codeLabel')}</Label>
						<Input
							id="totp-code"
							data-test-totp-code
							inputmode="numeric"
							autocomplete="one-time-code"
							maxlength={6}
							bind:value={code}
							required
						/>
					</div>
					{#if error}
						<p data-test-totp-error role="alert" class="text-sm text-destructive">{error}</p>
					{/if}
					<div class="flex flex-wrap gap-2">
						<Button data-test-totp-confirm type="submit" disabled={busy}>
							{busy ? t('totp.confirming') : t('totp.confirm')}
						</Button>
						<Button type="button" variant="ghost" onclick={reset}>{t('common.cancel')}</Button>
					</div>
				</form>
			</div>
		{:else if step === 'renewing'}
			<form data-test-totp-renew-form class="flex flex-col gap-3" onsubmit={renew}>
				<p class="text-sm text-muted-foreground">{t('totp.renewHint')}</p>
				<div class="flex flex-col gap-1.5">
					<Label for="totp-renew-code">{t('totp.codeLabel')}</Label>
					<Input
						id="totp-renew-code"
						data-test-totp-renew-code
						inputmode="numeric"
						autocomplete="one-time-code"
						maxlength={6}
						bind:value={code}
						required
					/>
				</div>
				{#if error}
					<p data-test-totp-error role="alert" class="text-sm text-destructive">{error}</p>
				{/if}
				<div class="flex flex-wrap gap-2">
					<Button type="submit" disabled={busy}>
						{busy ? t('common.saving') : t('totp.renew')}
					</Button>
					<Button type="button" variant="ghost" onclick={reset}>{t('common.cancel')}</Button>
				</div>
			</form>
		{:else if step === 'disabling'}
			<form data-test-totp-disable-form class="flex flex-col gap-3" onsubmit={disable}>
				<p class="text-sm text-muted-foreground">{t('totp.disableHint')}</p>
				<div class="flex flex-col gap-1.5">
					{#if disableWithPassword}
						<Label for="totp-disable-password">{t('totp.disablePassword')}</Label>
						<Input
							id="totp-disable-password"
							data-test-totp-disable-password
							type="password"
							autocomplete="current-password"
							bind:value={password}
							required
						/>
					{:else}
						<Label for="totp-disable-code">{t('totp.codeLabel')}</Label>
						<Input
							id="totp-disable-code"
							data-test-totp-disable-code
							inputmode="numeric"
							autocomplete="one-time-code"
							maxlength={6}
							bind:value={code}
							required
						/>
					{/if}
				</div>
				{#if error}
					<p data-test-totp-error role="alert" class="text-sm text-destructive">{error}</p>
				{/if}
				<div class="flex flex-wrap gap-2">
					<Button type="submit" variant="destructive" disabled={busy}>
						{busy ? t('totp.disabling') : t('totp.disable')}
					</Button>
					<Button type="button" variant="ghost" onclick={reset}>{t('common.cancel')}</Button>
				</div>
			</form>
		{:else if isEnabled}
			<div class="flex flex-col gap-3">
				<p data-test-totp-status class="text-sm font-medium">{t('totp.statusOn')}</p>
				<p
					data-test-totp-codes-left
					class={codesLeft <= LOW_RECOVERY_CODES
						? 'text-sm text-destructive'
						: 'text-sm text-muted-foreground'}
				>
					{codesLeft <= LOW_RECOVERY_CODES
						? t('totp.codesLow', { count: codesLeft })
						: t('totp.codesLeft', { count: codesLeft })}
				</p>
				{#if error}
					<p data-test-totp-error role="alert" class="text-sm text-destructive">{error}</p>
				{/if}
				<div class="flex flex-wrap gap-2">
					<Button
						data-test-totp-renew-open
						variant="outline"
						onclick={() => {
							error = null;
							step = 'renewing';
						}}
					>
						{t('totp.renew')}
					</Button>
					<Button
						data-test-totp-disable-open
						variant="ghost"
						onclick={() => {
							error = null;
							step = 'disabling';
						}}
					>
						{t('totp.disable')}
					</Button>
				</div>
			</div>
		{:else}
			<div class="flex flex-col gap-3">
				<p data-test-totp-status class="text-sm text-muted-foreground">{t('totp.statusOff')}</p>
				{#if error}
					<p data-test-totp-error role="alert" class="text-sm text-destructive">{error}</p>
				{/if}
				<Button data-test-totp-enable class="self-start" disabled={busy} onclick={startEnrolment}>
					{busy ? t('totp.starting') : t('totp.enable')}
				</Button>
			</div>
		{/if}
	</CardContent>
</Card>
