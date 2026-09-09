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
	import { t } from '$technical/i18n/i18n.svelte.js';
	import { LOCALES } from '$technical/i18n/locales';

	// Derived, so the two translated entries follow a language change like the rest of the screen.
	const AI_PROVIDERS = $derived<{ value: AIProvider | ''; label: string }[]>([
		{ value: '', label: t('ai.providerNone') },
		{ value: 'mistral', label: 'Mistral' },
		{ value: 'openai', label: 'OpenAI' },
		{ value: 'anthropic', label: 'Anthropic (Claude)' },
		{ value: 'gemma', label: 'Gemma' },
		{ value: 'custom', label: t('ai.providerCustom') }
	]);
	// The same ten as the interface, and named in their own language for the same reason.
	const LANGUAGES = LOCALES.map((locale) => ({
		value: locale.code as PreferredLanguage,
		label: locale.nativeLabel,
		translatable: locale.translatable
	}));

	let me = $state<Me | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let language = $state<PreferredLanguage>('fr');
	// Said plainly at the moment of the choice: a language no provider covers means the articles stay
	// in their original one, which is better learnt here than by wondering why nothing is translated.
	const translatableChoice = $derived(
		LANGUAGES.find((option) => option.value === language)?.translatable ?? true
	);
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
			error = t('ai.loadFailed');
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
			error = t('ai.saveFailed');
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
		await patch(payload, t('ai.saved'));
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
				{t('ai.title')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">
				{t('ai.intro')}
			</p>
		</div>

		{#if loading}
			<p data-test-ai-loading class="text-sm text-muted-foreground" aria-live="polite">
				{t('ai.loading')}
			</p>
		{:else if me === null}
			<p data-test-ai-unavailable class="text-sm text-destructive" aria-live="polite">
				{error ?? t('ai.unavailable')}
			</p>
		{:else}
			<fieldset class="flex flex-col gap-2">
				<legend class="mb-1 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
					<Languages class="size-4" />
					{t('ai.readingLanguage')}
				</legend>
				<p class="text-xs text-muted-foreground">
					{t('ai.readingLanguageHint')}
				</p>
				<!-- A select rather than a row of radios: ten of them wrap into an unreadable block, and
					 this list is a single choice out of a long set. -->
				<select
					data-test-reading-language
					bind:value={language}
					aria-label={t('ai.readingLanguage')}
					class="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					{#each LANGUAGES as option (option.value)}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>
				{#if !translatableChoice}
					<p
						data-test-language-untranslatable
						class="text-xs text-muted-foreground"
						aria-live="polite"
					>
						{t('ai.readingLanguageNoProvider')}
					</p>
				{/if}
			</fieldset>

			<div class="flex flex-col gap-2">
				<Label for="ai-provider">{t('ai.provider')}</Label>
				<select
					id="ai-provider"
					data-test-ai-provider
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
							{t('ai.apiKey')}
							{#if me.ai_api_key_set}
								<span class="ml-1 text-xs font-normal text-muted-foreground">
									{t('ai.keyOnFile')}
								</span>
							{/if}
						</Label>
						<Input
							id="ai-key"
							data-test-ai-key
							type="password"
							autocomplete="off"
							bind:value={aiApiKey}
							placeholder={me.ai_api_key_set ? t('ai.keyKeep') : 'sk-…'}
							aria-describedby="ai-key-hint"
						/>
						<p id="ai-key-hint" class="text-xs text-muted-foreground">
							{t('ai.keyHint')}
						</p>
					</div>

					<div class="flex flex-col gap-2">
						<Label for="ai-model">{t('ai.model')}</Label>
						<Input
							id="ai-model"
							data-test-ai-model
							bind:value={aiModel}
							placeholder={aiProvider === 'custom' ? 'voxtral-small' : t('ai.modelDefault')}
						/>
					</div>

					{#if aiProvider === 'custom'}
						<div class="flex flex-col gap-2">
							<Label for="ai-endpoint">{t('ai.endpoint')}</Label>
							<Input
								id="ai-endpoint"
								data-test-ai-endpoint
								type="url"
								bind:value={aiEndpointUrl}
								placeholder="http://voxtral.local/v1"
							/>
						</div>
					{/if}

					{#if me.ai_api_key_set}
						<Button
							data-test-delete-ai-key
							variant="outline"
							size="sm"
							class="self-start"
							disabled={saving}
							onclick={() => patch({ ai_api_key: null }, t('ai.summaryKeyDeleted'))}
						>
							{t('ai.deleteKey')}
						</Button>
					{/if}
				{/if}
			</div>

			<div class="flex flex-col gap-2">
				<Label for="translation-provider">{t('ai.translationProvider')}</Label>
				<select
					id="translation-provider"
					data-test-translation-provider
					bind:value={translationProvider}
					class="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					<option value="">{t('ai.translationNone')}</option>
					<option value="deepl">DeepL</option>
				</select>

				{#if translationProvider !== ''}
					<div class="flex flex-col gap-2">
						<Label for="translation-key">
							{t('ai.deeplKey')}
							{#if me.translation_api_key_set}
								<span class="ml-1 text-xs font-normal text-muted-foreground">
									{t('ai.keyOnFile')}
								</span>
							{/if}
						</Label>
						<Input
							id="translation-key"
							data-test-translation-key
							type="password"
							autocomplete="off"
							bind:value={translationApiKey}
							placeholder={me.translation_api_key_set ? t('ai.keyKeep') : 'xxxxxxxx-xxxx-…:fx'}
						/>
					</div>

					{#if me.translation_api_key_set}
						<Button
							data-test-delete-translation-key
							variant="outline"
							size="sm"
							class="self-start"
							disabled={saving}
							onclick={() => patch({ translation_api_key: null }, t('ai.deeplKeyDeleted'))}
						>
							{t('ai.deleteKey')}
						</Button>
					{/if}
				{/if}
			</div>

			{#if error}
				<p data-test-ai-error class="text-sm text-destructive" aria-live="polite">{error}</p>
			{/if}

			<Button data-test-ai-save class="self-start" disabled={saving} onclick={save}>
				{saving ? t('common.saving') : t('common.save')}
			</Button>
		{/if}
	</CardContent>
</Card>
