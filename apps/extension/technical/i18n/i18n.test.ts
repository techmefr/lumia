import { describe, expect, it } from 'vitest';
import { createTranslator, resolveLocale } from './i18n';
import { en } from './messages/en';
import { fr } from './messages/fr';

describe('resolveLocale', () => {
	it('follows the first browser language the extension has a catalogue for', () => {
		expect(resolveLocale(['de-DE', 'en-GB', 'fr'])).toBe('en');
	});

	it('falls back to French, the default of the app', () => {
		expect(resolveLocale(['ja'])).toBe('fr');
		expect(resolveLocale([])).toBe('fr');
	});
});

describe('createTranslator', () => {
	it('translates into the resolved language', () => {
		expect(createTranslator(['en-US'])('save.saved')).toBe(en['save.saved']);
		expect(createTranslator(['fr-FR'])('save.saved')).toBe(fr['save.saved']);
	});

	it('substitutes named placeholders', () => {
		expect(createTranslator(['en'])('reader.minutes', { count: 7 })).toBe('7 min');
	});

	it('leaves a placeholder alone when no value is given for it', () => {
		expect(createTranslator(['en'])('reader.minutes', { other: 1 })).toBe('{count} min');
	});

	it('has the same keys in every catalogue, so no language shows a raw key', () => {
		expect(Object.keys(en).sort()).toEqual(Object.keys(fr).sort());
	});
});
