import { beforeEach, describe, expect, it } from 'vitest';
import { getLocale, initLocale, setLocale, t } from './i18n.svelte';
import { LOCALES } from './locales';
import { fr } from './messages/fr';
import { ar } from './messages/ar';
import { de } from './messages/de';
import { en } from './messages/en';
import { es } from './messages/es';
import { it as italian } from './messages/it';
import { mg } from './messages/mg';
import { pt } from './messages/pt';
import { ru } from './messages/ru';
import { zh } from './messages/zh';

const CATALOGUES = { fr, en, es, de, it: italian, pt, ru, ar, zh, mg };
const CODES = Object.keys(CATALOGUES) as (keyof typeof CATALOGUES)[];
const KEYS = Object.keys(fr) as (keyof typeof fr)[];

const placeholdersOf = (value: string) =>
	[...value.matchAll(/\{(\w+)\}/g)].map((match) => match[1]).sort();

describe('the catalogues', () => {
	it('ships one for every language the settings offer', () => {
		expect(CODES.sort()).toEqual(LOCALES.map((locale) => locale.code).sort());
	});

	// The type system already forbids a missing key. These two catch what it cannot see: a key
	// present but left empty, and a placeholder that was dropped in translation.
	it.each(CODES)('leaves no empty string in %s', (code) => {
		const empty = KEYS.filter((key) => CATALOGUES[code][key].trim() === '');
		expect(empty).toEqual([]);
	});

	// A language may legitimately spell a singular out — arabic writes "one article" rather than
	// "1 article" — so dropping the count of a `*One` key loses nothing. Listed one by one rather
	// than matched by name, so a drop anywhere else still fails.
	const SPELLED_OUT_SINGULARS: Partial<Record<keyof typeof CATALOGUES, string[]>> = {
		ar: ['playlists.countOne']
	};

	it.each(CODES)('introduces no placeholder of its own in %s', (code) => {
		// An unknown placeholder has nothing to substitute, so it reaches the reader as literal
		// braces. That is always a bug, in every language.
		const invented = KEYS.filter((key) => {
			const allowed = placeholdersOf(fr[key]);
			return placeholdersOf(CATALOGUES[code][key]).some((name) => !allowed.includes(name));
		});
		expect(invented).toEqual([]);
	});

	it.each(CODES)('keeps every placeholder french declares in %s', (code) => {
		const exceptions = SPELLED_OUT_SINGULARS[code] ?? [];
		const dropped = KEYS.filter((key) => {
			if (exceptions.includes(key)) return false;
			const present = placeholdersOf(CATALOGUES[code][key]);
			return placeholdersOf(fr[key]).some((name) => !present.includes(name));
		});
		expect(dropped).toEqual([]);
	});
});

describe('t', () => {
	beforeEach(() => {
		setLocale('en');
	});

	it('translates into the active language', () => {
		expect(t('nav.playlists')).toBe(en['nav.playlists']);
		setLocale('fr');
		expect(t('nav.playlists')).toBe(fr['nav.playlists']);
	});

	it('substitutes a named placeholder', () => {
		expect(t('notifications.newArticles', { count: 12 })).toBe('12 new articles to read');
	});

	it('accepts a number as readily as a string', () => {
		expect(t('notifications.newArticles', { count: '12' })).toBe('12 new articles to read');
	});

	it('leaves a placeholder alone when no value is supplied for it', () => {
		expect(t('notifications.newArticles', { other: 'x' })).toContain('{count}');
	});

	it('returns the template untouched when no params are passed at all', () => {
		expect(t('notifications.newArticles')).toBe(en['notifications.newArticles']);
	});

	it('substitutes every occurrence, not only the first', () => {
		// A key with one placeholder is the norm; this guards the regex being global.
		const rendered = t('feeds.markAllReadIn', { name: 'Tech' });
		expect(rendered).not.toContain('{name}');
	});
});

describe('setLocale', () => {
	it('remembers the choice so a reload keeps the language', () => {
		setLocale('ru');
		expect(localStorage.getItem('lumia-locale')).toBe('ru');
		expect(getLocale()).toBe('ru');
	});

	it('ignores a language it has no catalogue for, rather than blanking the interface', () => {
		setLocale('de');
		setLocale('kl');
		expect(getLocale()).toBe('de');
	});

	it('sets the document language, which screen readers and hyphenation depend on', () => {
		setLocale('es');
		expect(document.documentElement.lang).toBe('es');
	});

	it('flips the document direction for arabic and back again', () => {
		setLocale('ar');
		expect(document.documentElement.dir).toBe('rtl');
		setLocale('en');
		expect(document.documentElement.dir).toBe('ltr');
	});
});

describe('initLocale', () => {
	it('applies the stored language to the document on boot', () => {
		setLocale('ar');
		document.documentElement.dir = '';
		initLocale();
		expect(document.documentElement.dir).toBe('rtl');
	});
});
