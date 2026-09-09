import { beforeEach, describe, expect, it } from 'vitest';
import {
	ACCENT_PRESETS,
	FONT_PAIR_PRESETS,
	FONT_SCALE_PRESETS,
	getAccentHue,
	getFontPair,
	getFontScale,
	getTheme,
	initPreferences,
	isReadingComfort,
	setAccent,
	setFontPair,
	setFontScale,
	setReadingComfort,
	setTheme,
	toggleTheme
} from './theme-store.svelte';

const root = () => document.documentElement;

beforeEach(() => {
	root().className = '';
	root().removeAttribute('style');
	delete root().dataset.fontPair;
	delete root().dataset.readingComfort;
	setTheme('light');
	setAccent(ACCENT_PRESETS[0].id);
	setFontScale('md');
	setFontPair(FONT_PAIR_PRESETS[0].id);
	setReadingComfort(false);
});

describe('the presets', () => {
	it('offers the nine accents the settings screen shows', () => {
		expect(ACCENT_PRESETS).toHaveLength(9);
	});

	it('offers five text sizes, up to large-print', () => {
		expect(FONT_SCALE_PRESETS.map((preset) => preset.id)).toEqual(['sm', 'md', 'lg', 'xl', 'xxl']);
		expect(FONT_SCALE_PRESETS.at(-1)!.scale).toBe(1.5);
	});

	it('offers four font pairs, each a serif and a sans', () => {
		expect(FONT_PAIR_PRESETS).toHaveLength(4);
		expect(
			FONT_PAIR_PRESETS.every((preset) => preset.serif !== '' && preset.sans !== '')
		).toBe(true);
	});

	// The ids are the stored value, so renaming one silently resets everybody's saved choice.
	it.each([
		['accent', ACCENT_PRESETS],
		['font scale', FONT_SCALE_PRESETS],
		['font pair', FONT_PAIR_PRESETS]
	] as const)('has no duplicate %s id', (_label, presets) => {
		const ids = presets.map((preset) => preset.id);
		expect(new Set(ids).size).toBe(ids.length);
	});

	it('carries no language in the preset data, only ids', () => {
		expect(JSON.stringify(ACCENT_PRESETS)).not.toMatch(/[éèêàç]/i);
	});
});

describe('the theme', () => {
	it('marks the document when dark, so the css variables switch', () => {
		setTheme('dark');
		expect(getTheme()).toBe('dark');
		expect(root().classList.contains('dark')).toBe(true);
	});

	it('unmarks it when light again', () => {
		setTheme('dark');
		setTheme('light');
		expect(root().classList.contains('dark')).toBe(false);
	});

	it('remembers the choice across a reload', () => {
		setTheme('dark');
		expect(localStorage.getItem('lumia-theme')).toBe('dark');
	});

	it('toggles between the two', () => {
		setTheme('light');
		toggleTheme();
		expect(getTheme()).toBe('dark');
		toggleTheme();
		expect(getTheme()).toBe('light');
	});

	it('re-derives the accent lightness, so an accent stays readable in both themes', () => {
		setAccent('bleu');
		const light = root().style.getPropertyValue('--primary');
		setTheme('dark');
		expect(root().style.getPropertyValue('--primary')).not.toBe(light);
	});
});

describe('the accent', () => {
	it('applies the hue of the chosen preset', () => {
		setAccent('vert');
		const hue = ACCENT_PRESETS.find((preset) => preset.id === 'vert')!.hue;
		expect(getAccentHue()).toBe(hue);
		expect(root().style.getPropertyValue('--primary')).toContain(String(hue));
	});

	it('drives the focus ring too, so keyboard focus follows the accent', () => {
		setAccent('rose');
		expect(root().style.getPropertyValue('--ring')).toBe(
			root().style.getPropertyValue('--primary')
		);
	});

	it('stores the id rather than the hue, so a palette tweak reaches saved choices', () => {
		setAccent('ambre');
		expect(localStorage.getItem('lumia-accent')).toBe('ambre');
	});

	it('ignores an unknown preset instead of blanking the accent', () => {
		setAccent('sarcelle');
		const before = getAccentHue();
		setAccent('fuchsia-inexistant');
		expect(getAccentHue()).toBe(before);
	});
});

describe('the text size', () => {
	it('scales the root font size, which every rem in the app follows', () => {
		setFontScale('xxl');
		expect(root().style.fontSize).toBe('24px');
	});

	it('is 16px at the default step', () => {
		setFontScale('md');
		expect(root().style.fontSize).toBe('16px');
	});

	it('stores the id', () => {
		setFontScale('lg');
		expect(localStorage.getItem('lumia-font-scale')).toBe('lg');
		expect(getFontScale()).toBe(1.15);
	});

	it('ignores an unknown step', () => {
		setFontScale('lg');
		setFontScale('enorme');
		expect(getFontScale()).toBe(1.15);
	});

	it('announces the layout change, so the fixed nav re-measures', () => {
		let resized = 0;
		const onResize = () => (resized += 1);
		window.addEventListener('resize', onResize);
		setFontScale('xl');
		window.removeEventListener('resize', onResize);
		expect(resized).toBeGreaterThan(0);
	});
});

describe('the font pair', () => {
	it('sets the attribute app.css keys its token overrides on', () => {
		setFontPair('magazine');
		expect(root().dataset.fontPair).toBe('magazine');
		expect(getFontPair()).toBe('magazine');
	});

	it('stores the id', () => {
		setFontPair('technique');
		expect(localStorage.getItem('lumia-font-pair')).toBe('technique');
	});

	it('ignores an unknown pair', () => {
		setFontPair('humaniste');
		setFontPair('gothique');
		expect(getFontPair()).toBe('humaniste');
	});
});

describe('reading comfort', () => {
	it('sets the attribute when on', () => {
		setReadingComfort(true);
		expect(root().dataset.readingComfort).toBe('on');
		expect(isReadingComfort()).toBe(true);
	});

	it('removes the attribute rather than setting it to off', () => {
		setReadingComfort(true);
		setReadingComfort(false);
		expect(root().dataset.readingComfort).toBeUndefined();
	});

	it('stores both states, so off is remembered as a choice', () => {
		setReadingComfort(true);
		expect(localStorage.getItem('lumia-reading-comfort')).toBe('on');
		setReadingComfort(false);
		expect(localStorage.getItem('lumia-reading-comfort')).toBe('off');
	});
});

describe('initPreferences', () => {
	it('paints every stored preference onto the document in one pass', () => {
		setAccent('cyan');
		setFontScale('xl');
		setFontPair('humaniste');
		setReadingComfort(true);

		root().removeAttribute('style');
		delete root().dataset.fontPair;
		delete root().dataset.readingComfort;

		initPreferences();

		expect(root().style.getPropertyValue('--primary')).not.toBe('');
		expect(root().style.fontSize).toBe(`${16 * 1.3}px`);
		expect(root().dataset.fontPair).toBe('humaniste');
		expect(root().dataset.readingComfort).toBe('on');
	});
});
