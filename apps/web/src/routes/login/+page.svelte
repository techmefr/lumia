<script lang="ts">
	import { goto } from '$app/navigation';
	import { ApiError } from '@lumia/core';
	import { lumia } from '$lib/client';

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

<h1>Connexion</h1>

<form onsubmit={submit}>
	<label>
		Email
		<input type="email" bind:value={email} required autocomplete="email" />
	</label>
	<label>
		Mot de passe
		<input type="password" bind:value={password} required autocomplete="current-password" />
	</label>
	{#if error}
		<p class="error">{error}</p>
	{/if}
	<button type="submit" disabled={loading}>{loading ? 'Connexion…' : 'Se connecter'}</button>
</form>

<p><a href="/onboarding">Premier lancement ? Créer le compte administrateur</a></p>

<style>
	form {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		max-width: 320px;
	}
	.error {
		color: #c0392b;
	}
</style>
