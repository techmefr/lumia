<script lang="ts">
	import { onMount } from 'svelte';
	import { ApiError, type Me } from '@lumia/core';
	import { Button, Card, CardContent, Input, Label, toast } from '@lumia/ui';
	import Lock from '@lucide/svelte/icons/lock';
	import { MIN_PASSWORD_LENGTH } from '$technical/auth/password';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';

	let me = $state<Me | null>(null);
	let currentPassword = $state('');
	let newPassword = $state('');
	let confirmation = $state('');
	let saving = $state(false);
	let error = $state<string | null>(null);

	// An account that came in through SSO or a magic link has nothing to prove: asking it for a
	// password it never had would leave it without a way to set one.
	const needsCurrent = $derived(me?.password_set ?? true);

	function validate(): string | null {
		if (newPassword.length < MIN_PASSWORD_LENGTH) {
			return t('password.tooShort', { count: MIN_PASSWORD_LENGTH });
		}
		if (newPassword !== confirmation) return t('password.mismatch');
		return null;
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = validate();
		if (error) return;

		saving = true;
		try {
			await lumia.user.changePassword(needsCurrent ? currentPassword : null, newPassword);
			currentPassword = '';
			newPassword = '';
			confirmation = '';
			// There is one now, whether or not there was before: the form asks for the current
			// password from here on.
			if (me) me = { ...me, password_set: true };
			toast(t('password.changed'));
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 401
					? t('password.wrongCurrent')
					: t('password.failed');
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		void lumia.user
			.getMe()
			.then((account) => {
				me = account;
			})
			.catch(() => {
				me = null;
			});
	});
</script>

<Card>
	<CardContent class="flex flex-col gap-6 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-lg font-semibold">
				<Lock class="size-5 text-primary" />
				{t('password.title')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">
				{needsCurrent ? t('password.intro') : t('password.setIntro')}
			</p>
		</div>

		<form data-test-password-form class="flex flex-col gap-4" onsubmit={submit}>
			{#if needsCurrent}
				<div class="flex flex-col gap-1.5">
					<Label for="current-password">{t('password.current')}</Label>
					<Input
						id="current-password"
						data-test-current-password
						type="password"
						autocomplete="current-password"
						bind:value={currentPassword}
						required
					/>
				</div>
			{/if}

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
				<p data-test-password-error role="alert" class="text-sm text-destructive">{error}</p>
			{/if}

			<Button data-test-password-submit type="submit" class="self-start" disabled={saving}>
				{saving ? t('password.submitting') : t('password.submit')}
			</Button>
		</form>
	</CardContent>
</Card>
