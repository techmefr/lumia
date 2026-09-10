<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, CardContent, Label } from '@lumia/ui';
	import Settings from '@lucide/svelte/icons/settings';
	import Sun from '@lucide/svelte/icons/sun';
	import Moon from '@lucide/svelte/icons/moon';
	import Check from '@lucide/svelte/icons/check';
	import { requireAuth } from '$technical/auth/require-auth';
	import AiSettings from '$domain/settings/ai-settings.svelte';
	import FilterRules from '$domain/settings/filter-rules.svelte';
	import NotificationSettings from '$domain/settings/notification-settings.svelte';
	import InstanceAdmin from '$domain/settings/instance-admin.svelte';
	import { lumia } from '$technical/api/client';
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
		isReadingComfort,
		setReadingComfort,
		type Theme
	} from '$technical/theme/theme-store.svelte.js';
	import { getLocale, setLocale, t } from '$technical/i18n/i18n.svelte.js';
	import { LOCALES } from '$technical/i18n/locales';

	let locale = $state(getLocale());

	/** The scale ids are stored values, so their labels live in the catalogues, not in the preset. */
	const SCALE_KEYS = {
		sm: 'settings.scale.sm',
		md: 'settings.scale.md',
		lg: 'settings.scale.lg',
		xl: 'settings.scale.xl',
		xxl: 'settings.scale.xxl'
	} as const;

	function scaleLabel(id: string): string {
		return id in SCALE_KEYS ? t(SCALE_KEYS[id as keyof typeof SCALE_KEYS]) : id;
	}

	/** Same reasoning as the scales: the ids are stored, their names belong to the catalogues. */
	const ACCENT_KEYS = {
		violet: 'settings.accent.violet',
		indigo: 'settings.accent.indigo',
		bleu: 'settings.accent.blue',
		cyan: 'settings.accent.cyan',
		sarcelle: 'settings.accent.teal',
		vert: 'settings.accent.green',
		ambre: 'settings.accent.amber',
		terracotta: 'settings.accent.terracotta',
		rose: 'settings.accent.rose'
	} as const;

	const PAIR_KEYS = {
		editorial: ['settings.pair.editorial', 'settings.pair.editorialHint'],
		magazine: ['settings.pair.magazine', 'settings.pair.magazineHint'],
		humaniste: ['settings.pair.humanist', 'settings.pair.humanistHint'],
		technique: ['settings.pair.technical', 'settings.pair.technicalHint']
	} as const;

	function accentLabel(id: string): string {
		return id in ACCENT_KEYS ? t(ACCENT_KEYS[id as keyof typeof ACCENT_KEYS]) : id;
	}

	function pairLabel(id: string): string {
		return id in PAIR_KEYS ? t(PAIR_KEYS[id as keyof typeof PAIR_KEYS][0]) : id;
	}

	function pairHint(id: string): string {
		return id in PAIR_KEYS ? t(PAIR_KEYS[id as keyof typeof PAIR_KEYS][1]) : '';
	}

	function pickLocale(code: string) {
		setLocale(code);
		locale = getLocale();
	}

	let theme = $state<Theme>('light');
	let accentHue = $state(0);
	let fontScale = $state(1);
	let fontPair = $state(FONT_PAIR_PRESETS[0].id);
	let comfort = $state(false);
	// The API is the real guard; hiding the section only spares a member a panel of 403s.
	let isAdmin = $state(false);

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

	function toggleComfort() {
		comfort = !comfort;
		setReadingComfort(comfort);
	}

	onMount(() => {
		if (!requireAuth()) return;
		theme = getTheme();
		accentHue = getAccentHue();
		fontScale = getFontScale();
		fontPair = getFontPair();
		comfort = isReadingComfort();
		void lumia.user
			.getMe()
			.then((me) => {
				isAdmin = me.role === 'admin';
			})
			.catch(() => {
				isAdmin = false;
			});
	});
</script>

<div class="mx-auto flex max-w-2xl flex-col gap-6">
	<h1 class="flex items-center gap-2 text-2xl font-semibold">
		<Settings class="size-6 text-primary" />
		{t('settings.title')}
	</h1>

	<Card>
		<CardContent class="flex flex-col gap-2 pt-6">
			<Label for="ui-locale">{t('settings.language')}</Label>
			<select
				id="ui-locale"
				value={locale}
				onchange={(event) => pickLocale(event.currentTarget.value)}
				class="h-10 max-w-xs rounded-md border border-input bg-background px-3 text-sm focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
			>
				{#each LOCALES as option (option.code)}
					<option value={option.code}>{option.nativeLabel}</option>
				{/each}
			</select>
			<p class="text-xs text-muted-foreground">{t('settings.languageHint')}</p>
		</CardContent>
	</Card>

	<Card>
		<CardContent class="pt-6">
			<fieldset class="flex flex-col gap-3">
				<legend class="mb-3 text-sm font-semibold text-muted-foreground">
					{t('settings.theme')}
				</legend>
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
						<span class="text-sm font-medium">{t('settings.themeLight')}</span>
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
						<span class="text-sm font-medium">{t('settings.themeDark')}</span>
					</label>
				</div>
			</fieldset>
		</CardContent>
	</Card>

	<Card>
		<CardContent class="pt-6">
			<fieldset class="flex flex-col gap-3">
				<legend class="mb-3 text-sm font-semibold text-muted-foreground">
					{t('settings.accent')}
				</legend>
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
							<span class="sr-only">{accentLabel(preset.id)}</span>
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
				<legend class="text-sm font-semibold text-muted-foreground">{t('settings.fontPair')}</legend>
				<p class="text-xs text-muted-foreground">{t('settings.fontPairHint')}</p>
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
								{pairLabel(preset.id)}
							</span>
							<span
								class="mt-1 block text-sm text-muted-foreground"
								style={`font-family: '${preset.sans}', system-ui, sans-serif;`}
							>
								{pairHint(preset.id)}
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
				<legend class="text-sm font-semibold text-muted-foreground">{t('settings.textSize')}</legend>
				<p class="text-xs text-muted-foreground">{t('settings.textSizeHint')}</p>
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
							<span class="sr-only">{scaleLabel(preset.id)}</span>
						</label>
					{/each}
				</div>
				<div aria-hidden="true" class="flex justify-between text-xs text-muted-foreground">
					{#each FONT_SCALE_PRESETS as preset (preset.id)}
						<span class="flex-1 text-center">{scaleLabel(preset.id)}</span>
					{/each}
				</div>
			</fieldset>

			<div class="flex flex-col gap-2 border-t pt-4">
				<span class="text-sm font-semibold text-muted-foreground">{t('settings.comfort')}</span>
				<p class="text-xs text-muted-foreground">{t('settings.comfortHint')}</p>
				<Button
					variant={comfort ? 'secondary' : 'outline'}
					size="sm"
					class="self-start"
					aria-pressed={comfort}
					onclick={toggleComfort}
				>
					{comfort ? t('settings.comfortOn') : t('settings.comfortOff')}
				</Button>
			</div>

			<div class="mt-2 rounded-lg border bg-muted/30 p-4">
				<h3 class="font-serif text-xl font-semibold">{t('settings.previewTitle')}</h3>
				<p class="prose mt-1 text-sm text-muted-foreground">{t('settings.previewBody')}</p>
				<span class="mt-2 block text-xs text-muted-foreground">
					{t('settings.previewCaption')}
				</span>
			</div>
		</CardContent>
	</Card>

	<NotificationSettings />

	<FilterRules />

	<AiSettings />

	{#if isAdmin}
		<InstanceAdmin />
	{/if}
</div>
