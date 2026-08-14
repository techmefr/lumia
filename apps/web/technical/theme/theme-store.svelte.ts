const THEME_KEY = 'lumia-theme';
const ACCENT_KEY = 'lumia-accent';
const FONT_SCALE_KEY = 'lumia-font-scale';
const FONT_PAIR_KEY = 'lumia-font-pair';

export type Theme = 'light' | 'dark';

export interface AccentPreset {
	id: string;
	label: string;
	hue: number;
}

// Colorblind-safe hues, distinct from the per-source avatar palette.
export const ACCENT_PRESETS: AccentPreset[] = [
	{ id: 'violet', label: 'Violet', hue: 265 },
	{ id: 'bleu', label: 'Bleu', hue: 220 },
	{ id: 'sarcelle', label: 'Sarcelle', hue: 175 },
	{ id: 'ambre', label: 'Ambre', hue: 50 },
	{ id: 'rose', label: 'Rose', hue: 340 }
];

export interface FontScalePreset {
	id: string;
	label: string;
	/** Multiplier applied to the 16px root — Tailwind's rem-based type scale keeps its
	 * golden-ratio-like step proportions since every size scales together. */
	scale: number;
}

export const FONT_SCALE_PRESETS: FontScalePreset[] = [
	{ id: 'sm', label: 'Petit', scale: 0.9 },
	{ id: 'md', label: 'Normal', scale: 1 },
	{ id: 'lg', label: 'Grand', scale: 1.15 },
	{ id: 'xl', label: 'Très grand', scale: 1.3 }
];

export interface FontPairPreset {
	id: string;
	label: string;
	/** What the pair is for, shown next to the sample so the choice isn't blind. */
	hint: string;
	serif: string;
	sans: string;
}

/**
 * Four pairs, each a serif for the titles and a sans for the running text. All four are
 * self-hosted from static/fonts; the ids double as the `data-font-pair` attribute values that
 * app.css keys its token overrides on.
 */
export const FONT_PAIR_PRESETS: FontPairPreset[] = [
	{
		id: 'editorial',
		label: 'Éditorial',
		hint: 'Sobre et neutre, lisible partout',
		serif: 'Source Serif 4',
		sans: 'Inter'
	},
	{
		id: 'magazine',
		label: 'Magazine',
		hint: 'Titres contrastés, presse papier',
		serif: 'Playfair Display',
		sans: 'Source Sans 3'
	},
	{
		id: 'humaniste',
		label: 'Humaniste',
		hint: 'Chaleureux, pour les textes longs',
		serif: 'Lora',
		sans: 'Work Sans'
	},
	{
		id: 'technique',
		label: 'Technique',
		hint: 'Rythme régulier, veille et code',
		serif: 'IBM Plex Serif',
		sans: 'IBM Plex Sans'
	}
];

function readInitialTheme(): Theme {
	if (typeof document === 'undefined') return 'light';
	return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

function readInitialAccentHue(): number {
	if (typeof localStorage === 'undefined') return ACCENT_PRESETS[0].hue;
	const stored = localStorage.getItem(ACCENT_KEY);
	const preset = ACCENT_PRESETS.find((p) => p.id === stored);
	return preset?.hue ?? ACCENT_PRESETS[0].hue;
}

function readInitialFontScale(): number {
	if (typeof localStorage === 'undefined') return 1;
	const stored = localStorage.getItem(FONT_SCALE_KEY);
	const preset = FONT_SCALE_PRESETS.find((p) => p.id === stored);
	return preset?.scale ?? 1;
}

function readInitialFontPair(): string {
	if (typeof localStorage === 'undefined') return FONT_PAIR_PRESETS[0].id;
	const stored = localStorage.getItem(FONT_PAIR_KEY);
	return FONT_PAIR_PRESETS.some((p) => p.id === stored) ? stored! : FONT_PAIR_PRESETS[0].id;
}

let theme = $state<Theme>(readInitialTheme());
let accentHue = $state<number>(readInitialAccentHue());
let fontScale = $state<number>(readInitialFontScale());
let fontPair = $state<string>(readInitialFontPair());

function applyAccent(hue: number, currentTheme: Theme) {
	const root = document.documentElement.style;
	const lightness = currentTheme === 'dark' ? 0.65 : 0.55;
	const accentLightness = currentTheme === 'dark' ? 0.3 : 0.94;
	const accentChroma = currentTheme === 'dark' ? 0.05 : 0.03;
	root.setProperty('--primary', `oklch(${lightness} 0.2 ${hue})`);
	root.setProperty('--ring', `oklch(${lightness} 0.2 ${hue})`);
	root.setProperty('--accent', `oklch(${accentLightness} ${accentChroma} ${hue})`);
}

function applyFontScale(scale: number) {
	document.documentElement.style.fontSize = `${16 * scale}px`;
	// Layout-affecting change: let listeners (e.g. the fixed bottom nav height tracker) re-measure.
	window.dispatchEvent(new Event('resize'));
}

export function getTheme(): Theme {
	return theme;
}

export function setTheme(next: Theme): void {
	theme = next;
	document.documentElement.classList.toggle('dark', next === 'dark');
	localStorage.setItem(THEME_KEY, next);
	applyAccent(accentHue, next);
}

export function toggleTheme(): void {
	setTheme(theme === 'dark' ? 'light' : 'dark');
}

export function getAccentHue(): number {
	return accentHue;
}

export function setAccent(presetId: string): void {
	const preset = ACCENT_PRESETS.find((p) => p.id === presetId);
	if (!preset) return;
	accentHue = preset.hue;
	localStorage.setItem(ACCENT_KEY, presetId);
	applyAccent(accentHue, theme);
}

function applyFontPair(id: string) {
	document.documentElement.dataset.fontPair = id;
	// The metrics of the new pair change every line box: let the bottom-nav tracker re-measure.
	window.dispatchEvent(new Event('resize'));
}

export function getFontPair(): string {
	return fontPair;
}

export function setFontPair(presetId: string): void {
	if (!FONT_PAIR_PRESETS.some((p) => p.id === presetId)) return;
	fontPair = presetId;
	localStorage.setItem(FONT_PAIR_KEY, presetId);
	applyFontPair(presetId);
}

export function getFontScale(): number {
	return fontScale;
}

export function setFontScale(presetId: string): void {
	const preset = FONT_SCALE_PRESETS.find((p) => p.id === presetId);
	if (!preset) return;
	fontScale = preset.scale;
	localStorage.setItem(FONT_SCALE_KEY, presetId);
	applyFontScale(fontScale);
}

export function initPreferences(): void {
	applyAccent(accentHue, theme);
	applyFontScale(fontScale);
	applyFontPair(fontPair);
}
