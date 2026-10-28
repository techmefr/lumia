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
	return (key: MessageKey): string => catalogue[key];
}

export const t = createTranslator(typeof navigator === 'undefined' ? [] : navigator.languages);
