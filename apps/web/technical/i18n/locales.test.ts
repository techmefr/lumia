import { describe, expect, it } from 'vitest';
import { DEFAULT_LOCALE, LOCALES, descriptorFor, resolvePreferred } from './locales';

describe('LOCALES', () => {
	it('offers the ten languages the app claims to speak', () => {
		expect(LOCALES.map((locale) => locale.code)).toEqual([
			'fr',
			'en',
			'es',
			'de',
			'it',
			'pt',
			'ru',
			'ar',
			'zh',
			'mg'
		]);
	});

	it('has no duplicate code, which would make the settings list ambiguous', () => {
		const codes = LOCALES.map((locale) => locale.code);
		expect(new Set(codes).size).toBe(codes.length);
	});

	it('names every language in that language, never in French', () => {
		expect(LOCALES.every((locale) => locale.nativeLabel.trim().length > 0)).toBe(true);
		expect(descriptorFor('de').nativeLabel).toBe('Deutsch');
		expect(descriptorFor('ru').nativeLabel).toBe('Русский');
	});

	it('marks arabic as the only right-to-left script', () => {
		expect(LOCALES.filter((locale) => locale.dir === 'rtl').map((l) => l.code)).toEqual(['ar']);
	});

	it('marks malagasy as the one language with no translation provider', () => {
		expect(LOCALES.filter((locale) => !locale.translatable).map((l) => l.code)).toEqual(['mg']);
	});
});

describe('descriptorFor', () => {
	it('finds the descriptor of a known code', () => {
		expect(descriptorFor('ar')).toMatchObject({ code: 'ar', dir: 'rtl' });
	});

	it('falls back to the first locale on an unknown code rather than returning undefined', () => {
		expect(descriptorFor('kl').code).toBe(DEFAULT_LOCALE);
	});

	it('does not match a region-qualified tag, which resolvePreferred is for', () => {
		expect(descriptorFor('pt-BR').code).toBe(DEFAULT_LOCALE);
	});
});

describe('resolvePreferred', () => {
	it('takes the first supported language the browser asks for', () => {
		expect(resolvePreferred(['de', 'en'])).toBe('de');
	});

	it('skips languages it cannot speak instead of giving up at the first miss', () => {
		expect(resolvePreferred(['nl', 'sv', 'it'])).toBe('it');
	});

	it('matches on the language subtag, so pt-BR lands on portuguese not french', () => {
		expect(resolvePreferred(['pt-BR'])).toBe('pt');
	});

	it('ignores the case of the tag', () => {
		expect(resolvePreferred(['ZH-Hant-TW'])).toBe('zh');
	});

	it('falls back to french when nothing matches', () => {
		expect(resolvePreferred(['nl', 'sv'])).toBe(DEFAULT_LOCALE);
	});

	it('falls back to french on an empty list', () => {
		expect(resolvePreferred([])).toBe(DEFAULT_LOCALE);
	});
});
