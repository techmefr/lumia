<script lang="ts">
	import { onMount } from 'svelte';
	import { Card, CardContent } from '@lumia/ui';
	import Settings from '@lucide/svelte/icons/settings';
	import Sun from '@lucide/svelte/icons/sun';
	import Moon from '@lucide/svelte/icons/moon';
	import Check from '@lucide/svelte/icons/check';
	import { requireAuth } from '$technical/auth/require-auth';
	import {
		getTheme,
		setTheme,
		getAccentHue,
		setAccent,
		ACCENT_PRESETS,
		getFontScale,
		setFontScale,
		FONT_SCALE_PRESETS,
		type Theme
	} from '$technical/theme/theme-store.svelte.js';

	let theme = $state<Theme>('light');
	let accentHue = $state(0);
	let fontScale = $state(1);

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

	onMount(() => {
		if (!requireAuth()) return;
		theme = getTheme();
		accentHue = getAccentHue();
		fontScale = getFontScale();
	});
</script>

<div class="mx-auto flex max-w-2xl flex-col gap-6">
	<h1 class="flex items-center gap-2 text-2xl font-semibold">
		<Settings class="size-6 text-primary" />
		Réglages d'apparence
	</h1>

	<Card>
		<CardContent class="flex flex-col gap-3 pt-6">
			<h2 class="text-sm font-semibold text-muted-foreground">Thème</h2>
			<div class="flex gap-3">
				<button
					onclick={() => pickTheme('light')}
					class="flex flex-1 flex-col items-center gap-2 rounded-xl border-2 p-4 transition-colors {theme ===
					'light'
						? 'border-primary'
						: 'border-border hover:border-muted-foreground'}"
				>
					<span
						class="flex size-10 items-center justify-center rounded-full bg-white text-zinc-900 shadow"
					>
						<Sun class="size-5" />
					</span>
					<span class="text-sm font-medium">Clair</span>
				</button>
				<button
					onclick={() => pickTheme('dark')}
					class="flex flex-1 flex-col items-center gap-2 rounded-xl border-2 p-4 transition-colors {theme ===
					'dark'
						? 'border-primary'
						: 'border-border hover:border-muted-foreground'}"
				>
					<span
						class="flex size-10 items-center justify-center rounded-full bg-zinc-900 text-white shadow"
					>
						<Moon class="size-5" />
					</span>
					<span class="text-sm font-medium">Sombre</span>
				</button>
			</div>
		</CardContent>
	</Card>

	<Card>
		<CardContent class="flex flex-col gap-3 pt-6">
			<h2 class="text-sm font-semibold text-muted-foreground">Couleur principale</h2>
			<div class="flex flex-wrap gap-3">
				{#each ACCENT_PRESETS as preset (preset.id)}
					<button
						onclick={() => pickAccent(preset.id)}
						aria-label={preset.label}
						class="flex size-11 items-center justify-center rounded-full ring-offset-2 ring-offset-background transition-transform hover:scale-110 {accentHue ===
						preset.hue
							? 'ring-2 ring-foreground'
							: ''}"
						style={`background: oklch(0.6 0.2 ${preset.hue});`}
					>
						{#if accentHue === preset.hue}
							<Check class="size-4 text-white drop-shadow" />
						{/if}
					</button>
				{/each}
			</div>
		</CardContent>
	</Card>

	<Card>
		<CardContent class="flex flex-col gap-3 pt-6">
			<h2 class="text-sm font-semibold text-muted-foreground">Taille du texte</h2>
			<p class="text-xs text-muted-foreground">
				La hiérarchie visuelle (titres, texte, légendes) garde toujours les mêmes proportions —
				seule la taille globale change.
			</p>
			<div class="flex gap-2">
				{#each FONT_SCALE_PRESETS as preset (preset.id)}
					<button
						onclick={() => pickFontScale(preset.id)}
						class="flex-1 rounded-lg border-2 py-2 text-sm font-medium transition-colors {fontScale ===
						preset.scale
							? 'border-primary bg-primary/10'
							: 'border-border hover:border-muted-foreground'}"
						style={`font-size: ${preset.scale}rem;`}
					>
						Aa
					</button>
				{/each}
			</div>
			<div class="flex justify-between text-xs text-muted-foreground">
				{#each FONT_SCALE_PRESETS as preset (preset.id)}
					<span class="flex-1 text-center">{preset.label}</span>
				{/each}
			</div>

			<div class="mt-2 rounded-lg border bg-muted/30 p-4">
				<h3 class="font-serif text-xl font-semibold">Aperçu du titre</h3>
				<p class="mt-1 text-sm text-muted-foreground">
					Un texte de résumé, pour vérifier que la hiérarchie reste lisible à toutes les tailles.
				</p>
				<span class="mt-2 block text-xs text-muted-foreground">Légende discrète</span>
			</div>
		</CardContent>
	</Card>
</div>
