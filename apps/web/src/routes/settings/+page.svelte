<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, CardContent } from '@lumia/ui';
	import Settings from '@lucide/svelte/icons/settings';
	import Sun from '@lucide/svelte/icons/sun';
	import Moon from '@lucide/svelte/icons/moon';
	import Check from '@lucide/svelte/icons/check';
	import { requireAuth } from '$technical/auth/require-auth';
	import AiSettings from '$domain/settings/ai-settings.svelte';
	import {
		getTheme,
		setTheme,
		getAccentHue,
		setAccent,
		ACCENT_PRESETS,
		getFontScale,
		setFontScale,
		FONT_SCALE_PRESETS,
		getFontPair,
		setFontPair,
		FONT_PAIR_PRESETS,
		type Theme
	} from '$technical/theme/theme-store.svelte.js';

	let theme = $state<Theme>('light');
	let accentHue = $state(0);
	let fontScale = $state(1);
	let fontPair = $state(FONT_PAIR_PRESETS[0].id);

	function pickTheme(next: Theme) {
		setTheme(next);
		theme = next;
	}

	function pickAccent(id: string) {
		setAccent(id);
		accentHue = getAccentHue();
	}

	function pickFontScale(id: string) {
		setFontScale(id);
		fontScale = getFontScale();
	}

	function pickFontPair(id: string) {
		setFontPair(id);
		fontPair = getFontPair();
	}

	onMount(() => {
		if (!requireAuth()) return;
		theme = getTheme();
		accentHue = getAccentHue();
		fontScale = getFontScale();
		fontPair = getFontPair();
	});
</script>

<div class="mx-auto flex max-w-2xl flex-col gap-6">
	<h1 class="flex items-center gap-2 text-2xl font-semibold">
		<Settings class="size-6 text-primary" />
		Réglages
	</h1>

	<Card>
		<CardContent class="pt-6">
			<fieldset class="flex flex-col gap-3">
				<legend class="mb-3 text-sm font-semibold text-muted-foreground">Thème</legend>
				<div class="flex gap-3">
					<label
						class="flex flex-1 cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-border p-4 transition-colors hover:border-muted-foreground has-[:checked]:border-primary has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2"
					>
						<input
							type="radio"
							name="theme"
							value="light"
							checked={theme === 'light'}
							onchange={() => pickTheme('light')}
							class="sr-only"
						/>
						<span
							class="flex size-10 items-center justify-center rounded-full bg-white text-zinc-900 shadow"
						>
							<Sun class="size-5" />
						</span>
						<span class="text-sm font-medium">Clair</span>
					</label>
					<label
						class="flex flex-1 cursor-pointer flex-col items-center gap-2 rounded-xl border-2 border-border p-4 transition-colors hover:border-muted-foreground has-[:checked]:border-primary has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2"
					>
						<input
							type="radio"
							name="theme"
							value="dark"
							checked={theme === 'dark'}
							onchange={() => pickTheme('dark')}
							class="sr-only"
						/>
						<span
							class="flex size-10 items-center justify-center rounded-full bg-zinc-900 text-white shadow"
						>
							<Moon class="size-5" />
						</span>
						<span class="text-sm font-medium">Sombre</span>
					</label>
				</div>
			</fieldset>
		</CardContent>
	</Card>

	<Card>
		<CardContent class="pt-6">
			<fieldset class="flex flex-col gap-3">
				<legend class="mb-3 text-sm font-semibold text-muted-foreground">Couleur principale</legend>
				<div class="flex flex-wrap gap-3">
					{#each ACCENT_PRESETS as preset (preset.id)}
						<label
							class="flex size-11 cursor-pointer items-center justify-center rounded-full ring-offset-2 ring-offset-background transition-transform hover:scale-110 has-[:checked]:ring-2 has-[:checked]:ring-foreground has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring"
							style={`background: oklch(0.6 0.2 ${preset.hue});`}
						>
							<input
								type="radio"
								name="accent"
								value={preset.id}
								checked={accentHue === preset.hue}
								onchange={() => pickAccent(preset.id)}
								class="sr-only"
							/>
							<span class="sr-only">{preset.label}</span>
							{#if accentHue === preset.hue}
								<Check class="size-4 text-white drop-shadow" />
							{/if}
						</label>
					{/each}
				</div>
			</fieldset>
		</CardContent>
	</Card>

	<Card>
		<CardContent class="pt-6">
			<fieldset class="flex flex-col gap-3">
				<legend class="text-sm font-semibold text-muted-foreground">Paire de polices</legend>
				<p class="text-xs text-muted-foreground">
					Un serif pour les titres, un sans pour le texte courant. Les quatre paires sont servies par
					ton instance : rien n'est chargé depuis un tiers.
				</p>
				<div class="grid gap-3 sm:grid-cols-2">
					{#each FONT_PAIR_PRESETS as preset (preset.id)}
						<label
							class="cursor-pointer rounded-xl border-2 border-border p-4 transition-colors hover:border-muted-foreground has-[:checked]:border-primary has-[:checked]:bg-primary/5 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2"
						>
							<input
								type="radio"
								name="font-pair"
								value={preset.id}
								checked={fontPair === preset.id}
								onchange={() => pickFontPair(preset.id)}
								class="sr-only"
							/>
							<span
								class="block text-lg font-semibold"
								style={`font-family: '${preset.serif}', Georgia, serif;`}
							>
								{preset.label}
							</span>
							<span
								class="mt-1 block text-sm text-muted-foreground"
								style={`font-family: '${preset.sans}', system-ui, sans-serif;`}
							>
								{preset.hint}
							</span>
						</label>
					{/each}
				</div>
			</fieldset>
		</CardContent>
	</Card>

	<Card>
		<CardContent class="flex flex-col gap-3 pt-6">
			<fieldset class="flex flex-col gap-3">
				<legend class="text-sm font-semibold text-muted-foreground">Taille du texte</legend>
				<p class="text-xs text-muted-foreground">
					La hiérarchie visuelle (titres, texte, légendes) garde toujours les mêmes proportions —
					seule la taille globale change.
				</p>
				<div class="flex gap-2">
					{#each FONT_SCALE_PRESETS as preset (preset.id)}
						<label
							class="flex-1 cursor-pointer rounded-lg border-2 border-border py-2 text-center text-sm font-medium transition-colors hover:border-muted-foreground has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:focus-visible]:ring-offset-2"
							style={`font-size: ${preset.scale}rem;`}
						>
							<input
								type="radio"
								name="font-scale"
								value={preset.id}
								checked={fontScale === preset.scale}
								onchange={() => pickFontScale(preset.id)}
								class="sr-only"
							/>
							<span aria-hidden="true">Aa</span>
							<span class="sr-only">{preset.label}</span>
						</label>
					{/each}
				</div>
				<div aria-hidden="true" class="flex justify-between text-xs text-muted-foreground">
					{#each FONT_SCALE_PRESETS as preset (preset.id)}
						<span class="flex-1 text-center">{preset.label}</span>
					{/each}
				</div>
			</fieldset>

			<div class="mt-2 rounded-lg border bg-muted/30 p-4">
				<h3 class="font-serif text-xl font-semibold">Aperçu du titre</h3>
				<p class="mt-1 text-sm text-muted-foreground">
					Un texte de résumé, pour vérifier que la hiérarchie reste lisible à toutes les tailles.
				</p>
				<span class="mt-2 block text-xs text-muted-foreground">Légende discrète</span>
			</div>
		</CardContent>
	</Card>

	<AiSettings />
</div>
