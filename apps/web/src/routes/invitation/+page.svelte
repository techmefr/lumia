<script lang="ts">
	import { base } from '$technical/paths/base';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { ApiError } from '@lumia/core';
	import { Button,
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle,
		Input,
		Label, Icon } from '@lumia/ui';
	import { UserAdd01Icon } from '@hugeicons/core-free-icons';
	import { MIN_PASSWORD_LENGTH } from '$technical/auth/password';
	import { lumia } from '$technical/api/client';
	import { stripQueryParam } from '$technical/url/strip-query-param';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let token = $state<string | null>(null);
	let username = $state('');
	let password = $state('');
	let confirmation = $state('');
	let saving = $state(false);
	let error = $state<string | null>(null);
	// Spent, expired, revoked or unknown all come back as the same 401, and none of them can be fixed
	// from this form, so the page stops offering it and says what to do instead.
	let spent = $state(false);

	function validate(): string | null {
		if (password.length < MIN_PASSWORD_LENGTH) {
			return t('password.tooShort', { count: MIN_PASSWORD_LENGTH });
		}
		if (password !== confirmation) return t('password.mismatch');
		return null;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		if (token === null) return;
		error = validate();
		if (error) return;

		saving = true;
		try {
			await lumia.user.acceptInvitation(token, username.trim(), password);
			await goto(base + '/articles');
		} catch (err) {
			if (err instanceof ApiError && err.status === 401) {
				spent = true;
				return;
			}
			// A 409 is the address having found an account elsewhere or the last seat going in the
			// meantime: only the admin can sort either out, so the message points there.
			error =
				err instanceof ApiError && err.status === 409
					? t('invitation.conflict')
					: t('invitation.failed');
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		token = page.url.searchParams.get('token');
		stripQueryParam('token');
	});
</script>

<div class="flex min-h-[80vh] items-center justify-center">
	<Card class="w-full max-w-sm animate-in fade-in zoom-in-95 duration-300">
		<CardHeader>
			<div
				class="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary"
			>
				<Icon icon={UserAdd01Icon} class="size-5" />
			</div>
			<CardTitle class="font-serif text-xl">{t('invitation.title')}</CardTitle>
			<CardDescription>{t('invitation.intro')}</CardDescription>
		</CardHeader>
		<CardContent>
			{#if token === null || spent}
				<p
					data-test-invitation-unusable
					role={spent ? 'alert' : 'status'}
					class="text-sm {spent ? 'text-destructive' : 'text-muted-foreground'}"
				>
					{spent ? t('invitation.invalidLink') : t('invitation.missingLink')}
				</p>
				<a
					data-test-sign-in-link
					href="{base}/login"
					class="mt-4 block text-center text-sm text-primary underline-offset-4 hover:underline"
				>
					{t('login.submit')}
				</a>
			{:else}
				<form data-test-invitation-form class="flex flex-col gap-4" onsubmit={submit}>
					<div class="flex flex-col gap-1.5">
						<Label for="invitation-username">{t('onboarding.username')}</Label>
						<Input
							id="invitation-username"
							data-test-username
							type="text"
							autocomplete="username"
							bind:value={username}
							required
						/>
					</div>
					<div class="flex flex-col gap-1.5">
						<Label for="invitation-password">{t('login.password')}</Label>
						<Input
							id="invitation-password"
							data-test-password
							type="password"
							autocomplete="new-password"
							minlength={MIN_PASSWORD_LENGTH}
							aria-describedby="invitation-password-hint"
							bind:value={password}
							required
						/>
						<p id="invitation-password-hint" class="text-xs text-muted-foreground">
							{t('password.tooShort', { count: MIN_PASSWORD_LENGTH })}
						</p>
					</div>
					<div class="flex flex-col gap-1.5">
						<Label for="invitation-confirm-password">{t('password.confirm')}</Label>
						<Input
							id="invitation-confirm-password"
							data-test-confirm-password
							type="password"
							autocomplete="new-password"
							bind:value={confirmation}
							required
						/>
					</div>
					{#if error}
						<p data-test-invitation-error role="alert" class="text-sm text-destructive">{error}</p>
					{/if}
					<Button type="submit" disabled={saving} class="mt-1">
						{saving ? t('password.submitting') : t('invitation.submit')}
					</Button>
				</form>
			{/if}
		</CardContent>
	</Card>
</div>
