<script lang="ts">
	import { goto } from '$app/navigation';
	import { ApiError } from '@lumia/core';
	import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle, Input, Label } from '@lumia/ui';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import LogIn from '@lucide/svelte/icons/log-in';
	import { lumia } from '$technical/api/client';

	let email = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let loading = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		loading = true;
		try {
			await lumia.user.login(email, password);
			await goto('/articles');
		} catch (err) {
			error = err instanceof ApiError && err.status === 401 ? 'Email ou mot de passe incorrect.' : "Connexion impossible.";
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex min-h-[80vh] items-center justify-center">
	<Card class="w-full max-w-sm animate-in fade-in zoom-in-95 duration-300">
		<CardHeader>
			<div class="mb-1 flex size-10 items-center justify-center rounded-full bg-primary/10 text-primary">
				<Sparkles class="size-5" />
			</div>
			<CardTitle class="font-serif text-xl">Lumia</CardTitle>
			<CardDescription>Connecte-toi pour retrouver tes flux.</CardDescription>
		</CardHeader>
		<CardContent>
			<form class="flex flex-col gap-4" onsubmit={submit}>
				<div class="flex flex-col gap-1.5">
					<Label for="email">Email</Label>
					<Input id="email" type="email" bind:value={email} required autocomplete="email" />
				</div>
				<div class="flex flex-col gap-1.5">
					<Label for="password">Mot de passe</Label>
					<Input
						id="password"
						type="password"
						bind:value={password}
						required
						autocomplete="current-password"
					/>
				</div>
				{#if error}
					<p class="text-sm text-destructive">{error}</p>
				{/if}
				<Button type="submit" disabled={loading} class="mt-1">
					<LogIn class="size-4" />
					{loading ? 'Connexion…' : 'Se connecter'}
				</Button>
			</form>
			<p class="mt-4 text-center text-sm text-muted-foreground">
				Premier lancement ?
				<a href="/onboarding" class="text-primary underline-offset-4 hover:underline"
					>Créer le compte administrateur</a
				>
			</p>
		</CardContent>
	</Card>
</div>
