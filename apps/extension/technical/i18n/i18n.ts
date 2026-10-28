import { fr, type Catalogue, type MessageKey } from './messages/fr';
import { en } from './messages/en';

export type { MessageKey };

const CATALOGUES: Record<string, Catalogue> = { fr, en };

export function resolveLocale(preferred: readonly string[]): string {
	for (const tag of preferred) {
		const code = tag.toLowerCase().split('-')[0];
		if (code in CATALOGUES) return code;
	}
	return 'fr';
}

export function createTranslator(preferred: readonly string[]) {
	const catalogue = CATALOGUES[resolveLocale(preferred)];
	return (key: MessageKey, params?: Record<string, string | number>): string => {
		const template = catalogue[key];
		if (!params) return template;
		return template.replace(/\{(\w+)\}/g, (match, name: string) =>
			name in params ? String(params[name]) : match
		);
	};
}

export const languages = typeof navigator === 'undefined' ? [] : navigator.languages;

export const locale = resolveLocale(languages);

export const t = createTranslator(languages);
