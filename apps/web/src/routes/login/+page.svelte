<script lang="ts">
	import { base } from '$technical/paths/base';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { createSignInFlow, type MagicLinkPurpose, type SignInOutcome, type SignInStep } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label, Icon } from '@lumia/ui';
	import { Login01Icon, Mail01Icon, SecurityCheckIcon, SparklesIcon } from '@hugeicons/core-free-icons';
	import { lumia } from '$technical/api/client';
	import InstanceUrlForm from '$domain/instance/instance-url-form.svelte';
	import { isNativePlatform } from '$technical/platform/native-platform';
	import { stripQueryParam } from '$technical/url/strip-query-param';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let loading = $state(false);

	// A token in the url means this page was opened from the magic-link email: verify it before
	// showing any form, rather than making the user re-enter it anywhere.
	let verifyingToken = $state(false);

	// The second factor is a step the shared flow decides on, once the backend says this account
	// has one; the page only draws it.
	const flow = createSignInFlow(lumia.user);
	let challenge = $state<SignInStep>('credentials');
	let totpCode = $state('');
	let recoveryCode = $state('');

	function failureMessage(outcome: SignInOutcome): string | null {
		if (outcome === 'wrong_code') return t('login.totpInvalid');
		if (outcome === 'bad_credentials') return t('login.badCredentials');
		if (outcome === 'failed') return t('login.failed');
		return null;
	}

	async function run(attempt: () => Promise<SignInOutcome>): Promise<boolean> {
		const outcome = await attempt();
		challenge = flow.step;
		error = failureMessage(outcome);
		return outcome === 'signed_in';
	}

	// The same form and the same token either way; only the mail, and the screen its link opens,
	// differ — a reader who cannot sign in has no use for a link that lands on the sign-in form.
	let magicMode = $state<MagicLinkPurpose | null>(null);
	let magicEmail = $state('');
	let magicLoading = $state(false);
	let magicSent = $state(false);

	function askFor(purpose: MagicLinkPurpose) {
		magicMode = purpose;
		magicSent = false;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		loading = true;
		try {
			const signedIn = await run(() =>
				challenge === 'credentials'
					? flow.signIn(email, password)
					: flow.submitSecondFactor(challenge === 'recovery' ? recoveryCode : totpCode)
			);
			if (signedIn) await goto(base + '/articles');
		} finally {
			loading = false;
		}
	}

	async function submitMagicLink(event: SubmitEvent) {
		event.preventDefault();
		if (magicMode === null) return;
		error = null;
		magicLoading = true;
		try {
			// The endpoint never reveals whether the address exists, so the message is the same
			// either way and there is nothing to branch on here.
			await lumia.user.requestMagicLink(magicEmail.trim(), magicMode);
			magicSent = true;
		} catch {
			error = t('login.failed');
		} finally {
			magicLoading = false;
		}
	}

	onMount(() => {
		const token = page.url.searchParams.get('magic_token');
		if (!token) return;
		stripQueryParam('magic_token');
		verifyingToken = true;
		flow
			.signInWithMagicLink(token)
			.then((outcome) => {
				challenge = flow.step;
				if (outcome === 'signed_in') return goto(base + '/articles');
				if (outcome !== 'challenge') error = t('login.magicLinkInvalid');
			})
			.catch(() => {
				error = t('login.magicLinkInvalid');
			})
			.finally(() => {
				verifyingToken = false;
			});
	});
</script>

<div class="flex min-h-[80vh] items-center justify-center">
	<Card class="w-full max-w-sm animate-in fade-in zoom-in-95 duration-300">
		<CardHeader>
			<div class="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
				<Icon icon={SparklesIcon} class="size-5" />
			</div>
			<CardTitle class="font-serif text-xl">Lumia</CardTitle>
			<CardDescription>{t('login.tagline')}</CardDescription>
		</CardHeader>
		<CardContent>
			{#if challenge !== 'credentials'}
				<form data-test-totp-form class="flex flex-col gap-4" onsubmit={submit}>
					<div class="flex items-center gap-2 text-sm font-medium">
						<Icon icon={SecurityCheckIcon} class="size-4 text-primary" />
						{t('login.totpTitle')}
					</div>
					{#if challenge === 'code'}
						<div class="flex flex-col gap-1.5">
							<Label for="totp-code">{t('login.totpCode')}</Label>
							<Input
								id="totp-code"
								data-test-totp-code
								inputmode="numeric"
								autocomplete="one-time-code"
								maxlength={6}
								bind:value={totpCode}
								required
							/>
							<p class="text-xs text-muted-foreground">{t('login.totpHint')}</p>
						</div>
					{:else}
						<div class="flex flex-col gap-1.5">
							<Label for="recovery-code">{t('login.recoveryCode')}</Label>
							<Input
								id="recovery-code"
								data-test-recovery-code
								autocomplete="one-time-code"
								bind:value={recoveryCode}
								required
							/>
							<p class="text-xs text-muted-foreground">{t('login.recoveryHint')}</p>
						</div>
					{/if}
					{#if error}
						<p role="alert" class="text-sm text-destructive">{error}</p>
					{/if}
					<Button type="submit" disabled={loading} class="mt-1">
						<Icon icon={Login01Icon} class="size-4" />
						{loading ? t('login.submitting') : t('login.totpSubmit')}
					</Button>
				</form>
				<button
					data-test-toggle-recovery
					type="button"
					onclick={() => {
						flow.toggleRecovery();
						challenge = flow.step;
						error = null;
					}}
					class="mt-4 block w-full text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
				>
					{challenge === 'code' ? t('login.useRecovery') : t('login.backToCode')}
				</button>
			{:else if verifyingToken}
				<p data-test-verifying-token role="status" class="py-6 text-center text-sm text-muted-foreground">
					{t('login.verifyingMagicLink')}
				</p>
			{:else if magicMode !== null}
				{#if magicSent}
					<p data-test-magic-sent role="status" class="text-sm text-muted-foreground">
						{magicMode === 'password_reset' ? t('login.resetSent') : t('login.magicLinkSent')}
					</p>
				{:else}
					<form data-test-magic-form class="flex flex-col gap-4" onsubmit={submitMagicLink}>
						{#if magicMode === 'password_reset'}
							<p data-test-reset-hint class="text-sm text-muted-foreground">
								{t('login.resetHint')}
							</p>
						{/if}
						<div class="flex flex-col gap-1.5">
							<Label for="magic-email">{t('login.email')}</Label>
							<Input
								id="magic-email"
								type="email"
								bind:value={magicEmail}
								required
								autocomplete="email"
							/>
						</div>
						{#if error}
							<p role="alert" class="text-sm text-destructive">{error}</p>
						{/if}
						<Button type="submit" disabled={magicLoading} class="mt-1">
							<Icon icon={Mail01Icon} class="size-4" />
							{magicLoading ? t('login.magicLinkSending') : t('login.magicLinkSubmit')}
						</Button>
					</form>
				{/if}
				<button
					data-test-back-to-password
					type="button"
					onclick={() => {
						magicMode = null;
						magicSent = false;
					}}
					class="mt-4 text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
				>
					{t('login.backToPassword')}
				</button>
			{:else}
				<form data-test-login-form class="flex flex-col gap-4" onsubmit={submit}>
					<div class="flex flex-col gap-1.5">
						<Label for="email">{t('login.email')}</Label>
						<Input id="email" type="email" bind:value={email} required autocomplete="email" />
					</div>
					<div class="flex flex-col gap-1.5">
						<Label for="password">{t('login.password')}</Label>
						<Input
							id="password"
							type="password"
							bind:value={password}
							required
							autocomplete="current-password"
						/>
					</div>
					{#if error}
						<p role="alert" class="text-sm text-destructive">{error}</p>
					{/if}
					<Button type="submit" disabled={loading} class="mt-1">
						<Icon icon={Login01Icon} class="size-4" />
						{loading ? t('login.submitting') : t('login.submit')}
					</Button>
				</form>
				<button
					data-test-magic-toggle
					type="button"
					onclick={() => askFor('sign_in')}
					class="mt-4 block w-full text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
				>
					{t('login.magicLinkToggle')}
				</button>
				<button
					data-test-forgot-password
					type="button"
					onclick={() => askFor('password_reset')}
					class="mt-2 block w-full text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
				>
					{t('login.forgotPassword')}
				</button>
				<p class="mt-4 text-center text-sm text-muted-foreground">
					{t('login.firstRun')}
					<a href="{base}/onboarding" class="text-primary underline-offset-4 hover:underline"
						>{t('login.createAdmin')}</a
					>
				</p>
			{/if}
			{#if isNativePlatform()}
				<div class="mt-6 border-t pt-4">
					<InstanceUrlForm />
				</div>
			{/if}
		</CardContent>
	</Card>
</div>
