/** The interface languages, in the order they are offered. */
export interface LocaleDescriptor {
	code: string;
	/** The name of the language written in that language: nobody looks for "Allemand" in a German UI. */
	nativeLabel: string;
	dir: 'ltr' | 'rtl';
}

export const LOCALES: LocaleDescriptor[] = [
	{ code: 'fr', nativeLabel: 'Français', dir: 'ltr' },
	{ code: 'en', nativeLabel: 'English', dir: 'ltr' },
	{ code: 'es', nativeLabel: 'Español', dir: 'ltr' },
	{ code: 'de', nativeLabel: 'Deutsch', dir: 'ltr' },
	{ code: 'it', nativeLabel: 'Italiano', dir: 'ltr' },
	{ code: 'pt', nativeLabel: 'Português', dir: 'ltr' },
	{ code: 'ru', nativeLabel: 'Русский', dir: 'ltr' },
	{ code: 'ar', nativeLabel: 'العربية', dir: 'rtl' },
	{ code: 'zh', nativeLabel: '中文', dir: 'ltr' },
	{ code: 'mg', nativeLabel: 'Malagasy', dir: 'ltr' }
];

export const DEFAULT_LOCALE = 'fr';

export function descriptorFor(code: string): LocaleDescriptor {
	return LOCALES.find((locale) => locale.code === code) ?? LOCALES[0];
}

/**
 * Picks a locale from what the browser asks for, matching on the language subtag only: `pt-BR` and
 * `pt-PT` both land on `pt`, which is closer than falling back to French.
 */
export function resolvePreferred(languages: readonly string[]): string {
	for (const language of languages) {
		const base = language.toLowerCase().split('-')[0];
		if (LOCALES.some((locale) => locale.code === base)) return base;
	}
	return DEFAULT_LOCALE;
}
