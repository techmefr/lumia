import { describe, expect, it } from 'vitest';
import {
	HELP_SHORTCUTS,
	NAVIGATION_PREFIX,
	NAVIGATION_SHORTCUTS,
	READING_SHORTCUTS
} from './shortcut-catalogue';
import { fr } from '$technical/i18n/messages/fr';

describe('the catalogue', () => {
	it('gives every navigation shortcut its own key', () => {
		const keys = NAVIGATION_SHORTCUTS.map((shortcut) => shortcut.key);
		expect(new Set(keys).size).toBe(keys.length);
	});

	it('spells each navigation shortcut as the prefix then its key', () => {
		for (const shortcut of NAVIGATION_SHORTCUTS) {
			expect(shortcut.keys).toEqual([NAVIGATION_PREFIX, shortcut.key]);
		}
	});

	it('points every navigation shortcut at an absolute route', () => {
		for (const shortcut of NAVIGATION_SHORTCUTS) expect(shortcut.href.startsWith('/')).toBe(true);
	});

	it('labels every entry with a key the catalogues actually carry', () => {
		for (const entry of [...NAVIGATION_SHORTCUTS, ...READING_SHORTCUTS, ...HELP_SHORTCUTS]) {
			expect(fr[entry.labelKey]).toBeTruthy();
		}
	});
});
