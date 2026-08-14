/**
 * Interface translation.
 *
 * Every catalogue is bundled rather than fetched: ten short dictionaries cost a few kilobytes, and
 * a language switch that needs a round trip would fail exactly where it matters — offline, or on the
 * static demo build with no backend behind it.
 */

import { DEFAULT_LOCALE, descriptorFor, resolvePreferred } from './locales';
import { fr, type Catalogue, type MessageKey } from './messages/fr';
import { en } from './messages/en';
import { es } from './messages/es';
import { de } from './messages/de';
import { it } from './messages/it';
import { pt } from './messages/pt';
import { ru } from './messages/ru';
import { ar } from './messages/ar';
import { zh } from './messages/zh';
import { mg } from './messages/mg';

const LOCALE_KEY = 'lumia-locale';

const CATALOGUES: Record<string, Catalogue> = { fr, en, es, de, it, pt, ru, ar, zh, mg };

function readInitialLocale(): string {
	if (typeof localStorage === 'undefined') return DEFAULT_LOCALE;
	const stored = localStorage.getItem(LOCALE_KEY);
	if (stored && stored in CATALOGUES) return stored;
	// No stored choice: follow the browser rather than imposing French on an English reader.
	return typeof navigator === 'undefined' ? DEFAULT_LOCALE : resolvePreferred(navigator.languages);
}

let locale = $state<string>(readInitialLocale());

export function getLocale(): string {
	return locale;
}

function apply(code: string): void {
	const descriptor = descriptorFor(code);
	document.documentElement.lang = descriptor.code;
	document.documentElement.dir = descriptor.dir;
}

export function setLocale(code: string): void {
	if (!(code in CATALOGUES)) return;
	locale = code;
	localStorage.setItem(LOCALE_KEY, code);
	apply(code);
}

export function initLocale(): void {
	apply(locale);
}

/**
 * Translates a key, substituting `{name}` placeholders.
 *
 * Reading `locale` here is what makes every call site reactive: a component that calls `t(...)` in
 * its markup re-renders on a language change without subscribing to anything.
 */
export function t(key: MessageKey, params?: Record<string, string | number>): string {
	const catalogue = CATALOGUES[locale] ?? fr;
	const template = catalogue[key] ?? fr[key];
	if (!params) return template;
	return template.replace(/\{(\w+)\}/g, (match, name: string) =>
		name in params ? String(params[name]) : match
	);
}
