<script lang="ts">
	import { base } from '$app/paths';
	import { goto } from '$app/navigation';
	import { ApiError } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label } from '@lumia/ui';
	import PartyPopper from '@lucide/svelte/icons/party-popper';
	import UserPlus from '@lucide/svelte/icons/user-plus';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';

	let email = $state('');
	let username = $state('');
	let password = $state('');
	// The key rather than the sentence: an error left on screen has to follow a language change too.
	let error = $state<MessageKey | null>(null);
	let loading = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		loading = true;
		try {
			await lumia.user.onboardAdmin({ email, username, password });
			await goto(base + '/articles');
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 409
					? 'onboarding.exists'
					: 'onboarding.failed';
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex min-h-[80vh] items-center justify-center">
	<Card class="w-full max-w-sm animate-in fade-in zoom-in-95 duration-300">
		<CardHeader>
			<div class="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
				<PartyPopper class="size-5" />
			</div>
			<CardTitle class="font-serif text-xl">{t('onboarding.title')}</CardTitle>
			<CardDescription>{t('onboarding.description')}</CardDescription>
		</CardHeader>
		<CardContent>
			<form class="flex flex-col gap-4" onsubmit={submit}>
				<div class="flex flex-col gap-1.5">
					<Label for="email">{t('login.email')}</Label>
					<Input id="email" type="email" bind:value={email} required autocomplete="email" />
				</div>
				<div class="flex flex-col gap-1.5">
					<Label for="username">{t('onboarding.username')}</Label>
					<Input id="username" type="text" bind:value={username} required autocomplete="username" />
				</div>
				<div class="flex flex-col gap-1.5">
					<Label for="password">{t('login.password')}</Label>
					<Input
						id="password"
						type="password"
						bind:value={password}
						required
						autocomplete="new-password"
					/>
				</div>
				{#if error}
					<p role="alert" class="text-sm text-destructive">{t(error)}</p>
				{/if}
				<Button type="submit" disabled={loading} class="mt-1">
					<UserPlus class="size-4" />
					{loading ? t('onboarding.submitting') : t('onboarding.submit')}
				</Button>
			</form>
		</CardContent>
	</Card>
</div>
