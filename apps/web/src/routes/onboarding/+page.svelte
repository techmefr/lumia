<script lang="ts">
	import { goto } from '$app/navigation';
	import { ApiError } from '@lumia/core';
	import { lumia } from '$lib/client';

	let email = $state('');
	let username = $state('');
	let password = $state('');
	let error = $state<string | null>(null);
	let loading = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		error = null;
		loading = true;
		try {
			await lumia.user.onboardAdmin({ email, username, password });
			await goto('/articles');
		} catch (err) {
			error =
				err instanceof ApiError && err.status === 409
					? 'Une instance existe déjà — connecte-toi normalement.'
					: 'Création du compte impossible.';
		} finally {
			loading = false;
		}
	}
</script>

<h1>Bienvenue sur Lumia</h1>
<p>Premier lancement : crée le compte administrateur de cette instance.</p>

<form onsubmit={submit}>
	<label>
		Email
		<input type="email" bind:value={email} required autocomplete="email" />
	</label>
	<label>
		Nom d'utilisateur
		<input type="text" bind:value={username} required autocomplete="username" />
	</label>
	<label>
		Mot de passe
		<input type="password" bind:value={password} required autocomplete="new-password" />
	</label>
	{#if error}
		<p class="error">{error}</p>
	{/if}
	<button type="submit" disabled={loading}>{loading ? 'Création…' : 'Créer le compte'}</button>
</form>

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
