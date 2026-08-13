const THEME_KEY = 'lumia-theme';
const ACCENT_KEY = 'lumia-accent';
const FONT_SCALE_KEY = 'lumia-font-scale';

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

let theme = $state<Theme>(readInitialTheme());
let accentHue = $state<number>(readInitialAccentHue());
let fontScale = $state<number>(readInitialFontScale());

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
}
