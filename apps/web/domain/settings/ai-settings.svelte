<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, CardContent, Input, Label, toast } from '@lumia/ui';
	import KeyRound from '@lucide/svelte/icons/key-round';
	import Languages from '@lucide/svelte/icons/languages';
	import type {
		AIProvider,
		Me,
		MeUpdate,
		PreferredLanguage,
		TranslationProvider
	} from '@lumia/core';
	import { lumia } from '$technical/api/client';

	const AI_PROVIDERS: { value: AIProvider | ''; label: string }[] = [
		{ value: '', label: 'Aucun — résumé local' },
		{ value: 'mistral', label: 'Mistral' },
		{ value: 'openai', label: 'OpenAI' },
		{ value: 'custom', label: 'Endpoint compatible OpenAI (auto-hébergé)' }
	];
	const LANGUAGES: { value: PreferredLanguage; label: string }[] = [
		{ value: 'fr', label: 'Français' },
		{ value: 'en', label: 'English' }
	];

	let me = $state<Me | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let language = $state<PreferredLanguage>('fr');
	let aiProvider = $state<AIProvider | ''>('');
	let aiModel = $state('');
	let aiEndpointUrl = $state('');
	let aiApiKey = $state('');
	let translationProvider = $state<TranslationProvider | ''>('');
	let translationApiKey = $state('');

	function hydrate(next: Me) {
		me = next;
		language = next.preferred_language;
		aiProvider = next.ai_provider ?? '';
		aiModel = next.ai_model ?? '';
		aiEndpointUrl = next.ai_endpoint_url ?? '';
		translationProvider = next.translation_provider ?? '';
		// The keys themselves never come back, so the fields stay empty: typing in one replaces
		// what is stored, leaving it blank keeps it.
		aiApiKey = '';
		translationApiKey = '';
	}

	async function load() {
		loading = true;
		error = null;
		try {
			hydrate(await lumia.user.getMe());
		} catch {
			error = 'Impossible de charger tes réglages.';
		} finally {
			loading = false;
		}
	}

	async function patch(payload: MeUpdate, message: string) {
		saving = true;
		error = null;
		try {
			hydrate(await lumia.user.updateMe(payload));
			toast(message);
		} catch {
			error = 'Enregistrement impossible. Vérifie la clé et réessaie.';
		} finally {
			saving = false;
		}
	}

	async function save() {
		const payload: MeUpdate = {
			preferred_language: language,
			ai_provider: aiProvider === '' ? null : aiProvider,
			ai_model: aiModel.trim() || null,
			ai_endpoint_url: aiEndpointUrl.trim() || null,
			translation_provider: translationProvider === '' ? null : translationProvider
		};
		// Omitted rather than sent empty: an empty string means "remove the key" server-side.
		if (aiApiKey.trim()) payload.ai_api_key = aiApiKey.trim();
		if (translationApiKey.trim()) payload.translation_api_key = translationApiKey.trim();
		await patch(payload, 'Réglages enregistrés.');
	}

	onMount(() => {
		void load();
	});
</script>

<Card>
	<CardContent class="flex flex-col gap-6 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-lg font-semibold">
				<KeyRound class="size-5 text-primary" />
				IA et traduction
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">
				Optionnel : les mots-clés et le résumé sont calculés localement. Une clé sert au résumé
				enrichi par un modèle et à la traduction des articles étrangers. Chaque compte pose la
				sienne — elle est chiffrée en base et n'est jamais renvoyée par l'API.
			</p>
		</div>

		{#if loading}
			<p class="text-sm text-muted-foreground" aria-live="polite">Chargement des réglages…</p>
		{:else if me === null}
			<p class="text-sm text-destructive" aria-live="polite">
				{error ?? 'Réglages indisponibles.'}
			</p>
		{:else}
			<fieldset class="flex flex-col gap-2">
				<legend class="mb-1 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
					<Languages class="size-4" />
					Langue de lecture
				</legend>
				<p class="text-xs text-muted-foreground">
					Les articles publiés dans une autre langue sont traduits vers celle-ci.
				</p>
				<div class="flex gap-2">
					{#each LANGUAGES as option (option.value)}
						<label
							class="flex-1 cursor-pointer rounded-lg border-2 border-border py-2 text-center text-sm font-medium transition-colors hover:border-muted-foreground has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2"
						>
							<input
								type="radio"
								name="preferred-language"
								value={option.value}
								checked={language === option.value}
								onchange={() => (language = option.value)}
								class="sr-only"
							/>
							{option.label}
						</label>
					{/each}
				</div>
			</fieldset>

			<div class="flex flex-col gap-2">
				<Label for="ai-provider">Fournisseur de résumé</Label>
				<select
					id="ai-provider"
					bind:value={aiProvider}
					class="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					{#each AI_PROVIDERS as option (option.value)}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>

				{#if aiProvider !== ''}
					<div class="flex flex-col gap-2">
						<Label for="ai-key">
							Clé d'API
							{#if me.ai_api_key_set}
								<span class="ml-1 text-xs font-normal text-muted-foreground">
									— une clé est enregistrée
								</span>
							{/if}
						</Label>
						<Input
							id="ai-key"
							type="password"
							autocomplete="off"
							bind:value={aiApiKey}
							placeholder={me.ai_api_key_set ? 'Laisser vide pour conserver la clé' : 'sk-…'}
							aria-describedby="ai-key-hint"
						/>
						<p id="ai-key-hint" class="text-xs text-muted-foreground">
							La clé n'est jamais réaffichée. Pour la retirer, utilise « Supprimer la clé ».
						</p>
					</div>

					<div class="flex flex-col gap-2">
						<Label for="ai-model">Modèle</Label>
						<Input
							id="ai-model"
							bind:value={aiModel}
							placeholder={aiProvider === 'custom' ? 'voxtral-small' : 'laisser vide = par défaut'}
						/>
					</div>

					{#if aiProvider === 'custom'}
						<div class="flex flex-col gap-2">
							<Label for="ai-endpoint">URL de l'endpoint</Label>
							<Input
								id="ai-endpoint"
								type="url"
								bind:value={aiEndpointUrl}
								placeholder="http://voxtral.local/v1"
							/>
						</div>
					{/if}

					{#if me.ai_api_key_set}
						<Button
							variant="outline"
							size="sm"
							class="self-start"
							disabled={saving}
							onclick={() => patch({ ai_api_key: null }, 'Clé de résumé supprimée.')}
						>
							Supprimer la clé
						</Button>
					{/if}
				{/if}
			</div>

			<div class="flex flex-col gap-2">
				<Label for="translation-provider">Fournisseur de traduction</Label>
				<select
					id="translation-provider"
					bind:value={translationProvider}
					class="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					<option value="">Aucun — pas de traduction</option>
					<option value="deepl">DeepL</option>
				</select>

				{#if translationProvider !== ''}
					<div class="flex flex-col gap-2">
						<Label for="translation-key">
							Clé DeepL
							{#if me.translation_api_key_set}
								<span class="ml-1 text-xs font-normal text-muted-foreground">
									— une clé est enregistrée
								</span>
							{/if}
						</Label>
						<Input
							id="translation-key"
							type="password"
							autocomplete="off"
							bind:value={translationApiKey}
							placeholder={me.translation_api_key_set
								? 'Laisser vide pour conserver la clé'
								: 'xxxxxxxx-xxxx-…:fx'}
						/>
					</div>

					{#if me.translation_api_key_set}
						<Button
							variant="outline"
							size="sm"
							class="self-start"
							disabled={saving}
							onclick={() => patch({ translation_api_key: null }, 'Clé DeepL supprimée.')}
						>
							Supprimer la clé
						</Button>
					{/if}
				{/if}
			</div>

			{#if error}
				<p class="text-sm text-destructive" aria-live="polite">{error}</p>
			{/if}

			<Button class="self-start" disabled={saving} onclick={save}>
				{saving ? 'Enregistrement…' : 'Enregistrer'}
			</Button>
		{/if}
	</CardContent>
</Card>
