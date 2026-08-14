/** The interface languages, in the order they are offered. */
export interface LocaleDescriptor {
	code: string;
	/** The name of the language written in that language: nobody looks for "Allemand" in a German UI. */
	nativeLabel: string;
	dir: 'ltr' | 'rtl';
	/** Whether articles can be machine-translated into it. Malagasy has no translation provider. */
	translatable: boolean;
}

export const LOCALES: LocaleDescriptor[] = [
	{ code: 'fr', nativeLabel: 'Français', dir: 'ltr', translatable: true },
	{ code: 'en', nativeLabel: 'English', dir: 'ltr', translatable: true },
	{ code: 'es', nativeLabel: 'Español', dir: 'ltr', translatable: true },
	{ code: 'de', nativeLabel: 'Deutsch', dir: 'ltr', translatable: true },
	{ code: 'it', nativeLabel: 'Italiano', dir: 'ltr', translatable: true },
	{ code: 'pt', nativeLabel: 'Português', dir: 'ltr', translatable: true },
	{ code: 'ru', nativeLabel: 'Русский', dir: 'ltr', translatable: true },
	{ code: 'ar', nativeLabel: 'العربية', dir: 'rtl', translatable: true },
	{ code: 'zh', nativeLabel: '中文', dir: 'ltr', translatable: true },
	{ code: 'mg', nativeLabel: 'Malagasy', dir: 'ltr', translatable: false }
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
