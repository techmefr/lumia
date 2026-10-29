<script lang="ts">
	import { createSignInFlow, type LumiaClient, type SignInOutcome } from '@lumia/core';
	import { Button, Input, Label } from '@lumia/ui';
	import type { ExtensionApi } from '$technical/browser/extension-api';
	import { openLumiaClient } from '$technical/api/lumia-session';
	import { t } from '$technical/i18n/i18n';

	let { extension, instanceUrl }: { extension: ExtensionApi; instanceUrl: string | null } =
		$props();

	let client = $state<LumiaClient | null>(null);
	let signedIn = $state(false);
	let email = $state('');
	let password = $state('');
	let code = $state('');
	let error = $state<string | null>(null);
	let busy = $state(false);
	let flow = $state<ReturnType<typeof createSignInFlow> | null>(null);
	let step = $state<'credentials' | 'code' | 'recovery'>('credentials');

	async function load() {
		client = await openLumiaClient(extension.storage.local);
		flow = client ? createSignInFlow(client.user) : null;
		step = 'credentials';
		signedIn = client !== null && client.tokenStore.getAccessToken() !== null;
	}

	$effect(() => {
		void instanceUrl;
		void load();
	});

	function failureMessage(outcome: SignInOutcome): string | null {
		if (outcome === 'wrong_code') return t('login.totpInvalid');
		if (outcome === 'bad_credentials') return t('login.badCredentials');
		if (outcome === 'failed') return t('login.failed');
		return null;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (flow === null) return;
		busy = true;
		try {
			const outcome =
				step === 'credentials'
					? await flow.signIn(email, password)
					: await flow.submitSecondFactor(code);
			step = flow.step;
			error = failureMessage(outcome);
			if (outcome === 'signed_in') {
				await client?.tokenStore.settled?.();
				signedIn = true;
				password = '';
				code = '';
			}
		} finally {
			busy = false;
		}
	}

	async function signOut() {
		try {
			await client?.user.logout();
		} finally {
			await client?.tokenStore.settled?.();
			signedIn = false;
		}
	}
</script>

{#if instanceUrl === null}
	<p data-test-need-instance class="text-sm text-muted-foreground">{t('settings.needInstance')}</p>
{:else if signedIn}
	<div class="flex flex-col gap-3">
		<p data-test-signed-in role="status" class="text-sm">{t('settings.signedIn')}</p>
		<Button data-test-sign-out variant="outline" onclick={signOut}>{t('settings.signOut')}</Button>
	</div>
{:else}
	<form data-test-sign-in-form class="flex flex-col gap-3" onsubmit={submit}>
		{#if step === 'credentials'}
			<div class="flex flex-col gap-1.5">
				<Label for="email">{t('login.email')}</Label>
				<Input id="email" type="email" autocomplete="email" bind:value={email} required />
			</div>
			<div class="flex flex-col gap-1.5">
				<Label for="password">{t('login.password')}</Label>
				<Input
					id="password"
					type="password"
					autocomplete="current-password"
					bind:value={password}
					required
				/>
			</div>
		{:else}
			<h3 class="text-sm font-medium">{t('login.totpTitle')}</h3>
			<div class="flex flex-col gap-1.5">
				<Label for="second-factor">
					{step === 'code' ? t('login.totpCode') : t('login.recoveryCode')}
				</Label>
				<Input
					id="second-factor"
					autocomplete="one-time-code"
					inputmode={step === 'code' ? 'numeric' : 'text'}
					bind:value={code}
					required
				/>
				<p class="text-xs text-muted-foreground">
					{step === 'code' ? t('login.totpHint') : t('login.recoveryHint')}
				</p>
			</div>
		{/if}
		{#if error}
			<p data-test-sign-in-error role="alert" class="text-sm text-destructive">{error}</p>
		{/if}
		<Button type="submit" disabled={busy}>
			{#if busy}
				{t('login.submitting')}
			{:else if step === 'credentials'}
				{t('login.submit')}
			{:else}
				{t('login.totpSubmit')}
			{/if}
		</Button>
		{#if step !== 'credentials'}
			<button
				data-test-toggle-recovery
				type="button"
				class="text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
				onclick={() => {
					flow?.toggleRecovery();
					step = flow?.step ?? 'credentials';
					error = null;
					code = '';
				}}
			>
				{step === 'code' ? t('login.useRecovery') : t('login.backToCode')}
			</button>
		{/if}
	</form>
{/if}
