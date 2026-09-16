<script lang="ts">
	import { base } from '$app/paths';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { ApiError } from '@lumia/core';
	import {
		Button,
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
		Input,
		Label
	} from '@lumia/ui';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import { MIN_PASSWORD_LENGTH } from '$technical/auth/password';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let token = $state<string | null>(null);
	let newPassword = $state('');
	let confirmation = $state('');
	let saving = $state(false);
	let error = $state<string | null>(null);

	function validate(): string | null {
		if (newPassword.length < MIN_PASSWORD_LENGTH) {
			return t('password.tooShort', { count: MIN_PASSWORD_LENGTH });
		}
		if (newPassword !== confirmation) return t('password.mismatch');
		return null;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (token === null) return;
		error = validate();
		if (error) return;

		saving = true;
		try {
			await lumia.user.resetPassword(token, newPassword);
			await goto(base + '/articles');
		} catch (err) {
			// The token is single-use and short-lived, so a refusal is the link being spent or
			// stale rather than anything the reader typed in the form.
			error =
				err instanceof ApiError && err.status === 401
					? t('reset.invalidLink')
					: t('password.failed');
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		token = page.url.searchParams.get('magic_token');
	});
</script>

<div class="flex min-h-[80vh] items-center justify-center">
	<Card class="w-full max-w-sm animate-in fade-in zoom-in-95 duration-300">
		<CardHeader>
			<div
				class="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary"
			>
				<KeyRound class="size-5" />
			</div>
			<CardTitle class="font-serif text-xl">{t('reset.title')}</CardTitle>
			<CardDescription>{t('reset.intro')}</CardDescription>
		</CardHeader>
		<CardContent>
			{#if token === null}
				<p data-test-missing-link role="status" class="text-sm text-muted-foreground">
					{t('reset.missingLink')}
				</p>
				<a
					href="{base}/login"
					class="mt-4 block text-center text-sm text-primary underline-offset-4 hover:underline"
				>
					{t('login.submit')}
				</a>
			{:else}
				<form data-test-reset-form class="flex flex-col gap-4" onsubmit={submit}>
					<div class="flex flex-col gap-1.5">
						<Label for="new-password">{t('password.new')}</Label>
						<Input
							id="new-password"
							data-test-new-password
							type="password"
							autocomplete="new-password"
							minlength={MIN_PASSWORD_LENGTH}
							bind:value={newPassword}
							required
						/>
					</div>
					<div class="flex flex-col gap-1.5">
						<Label for="confirm-password">{t('password.confirm')}</Label>
						<Input
							id="confirm-password"
							data-test-confirm-password
							type="password"
							autocomplete="new-password"
							bind:value={confirmation}
							required
						/>
					</div>
					{#if error}
						<p data-test-reset-error role="alert" class="text-sm text-destructive">{error}</p>
					{/if}
					<Button type="submit" disabled={saving} class="mt-1">
						{saving ? t('password.submitting') : t('reset.submit')}
					</Button>
				</form>
			{/if}
		</CardContent>
	</Card>
</div>
