<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, CardContent, Input, Label, toast } from '@lumia/ui';
	import AudioLines from '@lucide/svelte/icons/audio-lines';
	import type { Me, MeUpdate, TtsProvider } from '@lumia/core';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte.js';
	import { resetServerVoice } from '$technical/speech/server-voice';

	const PROVIDERS = $derived<{ value: TtsProvider | ''; label: string }[]>([
		{ value: '', label: t('tts.providerNone') },
		{ value: 'openai', label: 'OpenAI' },
		{ value: 'custom', label: t('tts.providerCustom') }
	]);

	let me = $state<Me | null>(null);
	let loading = $state(true);
	let saving = $state(false);
	let error = $state<string | null>(null);

	let provider = $state<TtsProvider | ''>('');
	let model = $state('');
	let voice = $state('');
	let endpointUrl = $state('');
	let apiKey = $state('');

	function hydrate(next: Me) {
		me = next;
		provider = next.tts_provider ?? '';
		model = next.tts_model ?? '';
		voice = next.tts_voice ?? '';
		endpointUrl = next.tts_endpoint_url ?? '';
		// The key never comes back: typing replaces it, leaving the field blank keeps it.
		apiKey = '';
	}

	async function load() {
		loading = true;
		error = null;
		try {
			hydrate(await lumia.user.getMe());
		} catch {
			error = t('tts.loadFailed');
		} finally {
			loading = false;
		}
	}

	async function patch(payload: MeUpdate, message: string) {
		saving = true;
		error = null;
		try {
			hydrate(await lumia.user.updateMe(payload));
			resetServerVoice();
			toast(message);
		} catch {
			error = t('tts.saveFailed');
		} finally {
			saving = false;
		}
	}

	async function save() {
		const payload: MeUpdate = {
			tts_provider: provider === '' ? null : provider,
			tts_model: model.trim() || null,
			tts_voice: voice.trim() || null,
			tts_endpoint_url: endpointUrl.trim() || null
		};
		// Omitted rather than sent empty: an empty string means "remove the key" server-side.
		if (apiKey.trim()) payload.tts_api_key = apiKey.trim();
		await patch(payload, t('tts.saved'));
	}

	onMount(() => {
		void load();
	});
</script>

<Card>
	<CardContent class="flex flex-col gap-6 pt-6">
		<div>
			<h2 class="flex items-center gap-2 text-lg font-semibold">
				<AudioLines class="size-5 text-primary" />
				{t('tts.title')}
			</h2>
			<p class="mt-1 text-sm text-muted-foreground">{t('tts.intro')}</p>
		</div>

		{#if loading}
			<p data-test-tts-loading class="text-sm text-muted-foreground" aria-live="polite">
				{t('tts.loading')}
			</p>
		{:else if me === null}
			<p data-test-tts-unavailable class="text-sm text-destructive" aria-live="polite">
				{error ?? t('tts.loadFailed')}
			</p>
		{:else}
			<div class="flex flex-col gap-2">
				<Label for="tts-provider">{t('tts.provider')}</Label>
				<select
					id="tts-provider"
					data-test-tts-provider
					bind:value={provider}
					class="h-10 rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
				>
					{#each PROVIDERS as option (option.value)}
						<option value={option.value}>{option.label}</option>
					{/each}
				</select>

				{#if provider !== ''}
					<div class="flex flex-col gap-2">
						<Label for="tts-key">
							{t('ai.apiKey')}
							{#if me.tts_api_key_set}
								<span class="ml-1 text-xs font-normal text-muted-foreground">
									{t('ai.keyOnFile')}
								</span>
							{/if}
						</Label>
						<Input
							id="tts-key"
							data-test-tts-key
							type="password"
							autocomplete="off"
							bind:value={apiKey}
							placeholder={me.tts_api_key_set ? t('ai.keyKeep') : 'sk-…'}
						/>
					</div>

					<div class="flex flex-col gap-2">
						<Label for="tts-model">{t('ai.model')}</Label>
						<Input
							id="tts-model"
							data-test-tts-model
							bind:value={model}
							placeholder={provider === 'custom' ? 'kokoro' : t('tts.voiceDefault')}
						/>
					</div>

					<div class="flex flex-col gap-2">
						<Label for="tts-voice">{t('tts.voice')}</Label>
						<Input
							id="tts-voice"
							data-test-tts-voice
							bind:value={voice}
							placeholder={t('tts.voiceDefault')}
						/>
					</div>

					{#if provider === 'custom'}
						<div class="flex flex-col gap-2">
							<Label for="tts-endpoint">{t('ai.endpoint')}</Label>
							<Input
								id="tts-endpoint"
								data-test-tts-endpoint
								type="url"
								bind:value={endpointUrl}
								placeholder="https://voice.example.com/v1"
								aria-describedby="tts-endpoint-hint"
							/>
							<p id="tts-endpoint-hint" class="text-xs text-muted-foreground">
								{t('tts.endpointHint')}
							</p>
						</div>
					{/if}

					{#if me.tts_api_key_set}
						<Button
							data-test-delete-tts-key
							variant="outline"
							size="sm"
							class="self-start"
							disabled={saving}
							onclick={() => patch({ tts_api_key: null }, t('tts.keyDeleted'))}
						>
							{t('ai.deleteKey')}
						</Button>
					{/if}
				{/if}
			</div>

			{#if error}
				<p data-test-tts-error class="text-sm text-destructive" aria-live="polite">{error}</p>
			{/if}

			<Button data-test-tts-save class="self-start" disabled={saving} onclick={save}>
				{saving ? t('common.saving') : t('common.save')}
			</Button>
		{/if}
	</CardContent>
</Card>
