<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { ApiError } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label } from '@lumia/ui';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import LogIn from '@lucide/svelte/icons/log-in';
	import Mail from '@lucide/svelte/icons/mail';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let loading = $state(false);

	// A token in the url means this page was opened from the magic-link email: verify it before
	// showing any form, rather than making the user re-enter it anywhere.
	let verifyingToken = $state(false);

	let magicMode = $state(false);
	let magicEmail = $state('');
	let magicLoading = $state(false);
	let magicSent = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		loading = true;
		try {
			await lumia.user.login(email, password);
			await goto(base + '/articles');
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 401
					? t('login.badCredentials')
					: t('login.failed');
		} finally {
			loading = false;
		}
	}

	async function submitMagicLink(event: SubmitEvent) {
		event.preventDefault();
		magicLoading = true;
		try {
			// The endpoint never reveals whether the address exists, so the message is the same
			// either way and there is nothing to branch on here.
			await lumia.user.requestMagicLink(magicEmail.trim());
			magicSent = true;
		} finally {
			magicLoading = false;
		}
	}

	onMount(() => {
		const token = page.url.searchParams.get('magic_token');
		if (!token) return;
		verifyingToken = true;
		lumia.user
			.verifyMagicLink(token)
			.then(() => goto(base + '/articles'))
			.catch(() => {
				verifyingToken = false;
				error = t('login.magicLinkInvalid');
			});
	});
</script>

<div class="flex min-h-[80vh] items-center justify-center">
	<Card class="w-full max-w-sm animate-in fade-in zoom-in-95 duration-300">
		<CardHeader>
			<div class="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
				<Sparkles class="size-5" />
			</div>
			<CardTitle class="font-serif text-xl">Lumia</CardTitle>
			<CardDescription>{t('login.tagline')}</CardDescription>
		</CardHeader>
		<CardContent>
			{#if verifyingToken}
				<p data-test-verifying-token role="status" class="py-6 text-center text-sm text-muted-foreground">
					{t('login.verifyingMagicLink')}
				</p>
			{:else if magicMode}
				{#if magicSent}
					<p data-test-magic-sent role="status" class="text-sm text-muted-foreground">
						{t('login.magicLinkSent')}
					</p>
				{:else}
					<form data-test-magic-form class="flex flex-col gap-4" onsubmit={submitMagicLink}>
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
						<Button type="submit" disabled={magicLoading} class="mt-1">
							<Mail class="size-4" />
							{magicLoading ? t('login.magicLinkSending') : t('login.magicLinkSubmit')}
						</Button>
					</form>
				{/if}
				<button
					data-test-back-to-password
					type="button"
					onclick={() => {
						magicMode = false;
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
						<LogIn class="size-4" />
						{loading ? t('login.submitting') : t('login.submit')}
					</Button>
				</form>
				<button
					data-test-magic-toggle
					type="button"
					onclick={() => (magicMode = true)}
					class="mt-4 block w-full text-center text-sm text-muted-foreground underline-offset-4 hover:underline"
				>
					{t('login.magicLinkToggle')}
				</button>
				<p class="mt-4 text-center text-sm text-muted-foreground">
					{t('login.firstRun')}
					<a href="{base}/onboarding" class="text-primary underline-offset-4 hover:underline"
						>{t('login.createAdmin')}</a
					>
				</p>
			{/if}
		</CardContent>
	</Card>
</div>
