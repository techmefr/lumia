import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { THEME_PRESETS } from './theme-store.svelte';

const css = readFileSync(resolve(process.cwd(), 'src/app.css'), 'utf8');

function paletteOf(id: string): Record<string, string> {
	const block = css.match(new RegExp(`\\[data-theme='${id}'\\] \\{([^}]*)\\}`));
	expect(block, `app.css declares a palette for ${id}`).not.toBeNull();
	const palette: Record<string, string> = {};
	for (const [, name, value] of block![1].matchAll(/--([\w-]+):\s*([^;]+);/g)) {
		palette[name] = value.trim();
	}
	return palette;
}

function luminance(hex: string): number {
	const [r, g, b] = [1, 3, 5].map((start) => {
		const channel = parseInt(hex.slice(start, start + 2), 16) / 255;
		return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(foreground: string, background: string): number {
	const [light, dark] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
	return (light + 0.05) / (dark + 0.05);
}

const TEXT_PAIRS = [
	['foreground', 'background'],
	['card-foreground', 'card'],
	['popover-foreground', 'popover'],
	['muted-foreground', 'background'],
	['muted-foreground', 'card'],
	['muted-foreground', 'muted'],
	['secondary-foreground', 'secondary'],
	['accent-foreground', 'accent'],
	['primary-foreground', 'primary'],
	['destructive-foreground', 'destructive'],
	['primary', 'background'],
	['primary', 'card'],
	['destructive', 'background']
] as const;

const named = THEME_PRESETS.filter((preset) => preset.named);
const namedEntries = named.map((preset) => [preset.id, preset] as const);

describe('the named palettes', () => {
	it('offers Dracula, its light variant Alucard and three more', () => {
		expect(named.map((preset) => preset.id)).toEqual([
			'dracula',
			'alucard',
			'nord',
			'solarized-light',
			'solarized-dark'
		]);
	});

	it('has no duplicate theme id', () => {
		const ids = THEME_PRESETS.map((preset) => preset.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it.each(namedEntries)('%s reaches 4.5:1 on every text pair', (id) => {
		const palette = paletteOf(id);
		for (const [foreground, background] of TEXT_PAIRS) {
			expect(
				contrast(palette[foreground], palette[background]),
				`${id}: ${foreground} on ${background}`
			).toBeGreaterThanOrEqual(4.5);
		}
	});

	it.each(namedEntries)('%s declares the same darkness as its background', (id, preset) => {
		expect(preset.dark).toBe(luminance(paletteOf(id).background) < 0.18);
	});

	it.each(namedEntries)('%s paints the browser chrome with its own background', (id, preset) => {
		expect(preset.themeColor).toBe(paletteOf(id).background);
	});

	it('keeps the early script in app.html in step with the table', () => {
		const html = readFileSync(resolve(process.cwd(), 'static/theme-boot.js'), 'utf8');
		for (const preset of named) {
			const key = preset.id.includes('-') ? `'${preset.id}'` : preset.id;
			expect(html).toContain(`${key}: { dark: ${preset.dark}, color: '${preset.themeColor}' }`);
		}
	});
});
