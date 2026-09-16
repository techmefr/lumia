/**
 * The off switch for single-character shortcuts, required by WCAG 2.1.4: a key that acts on its own
 * press has to be silenceable, because speech input turns dictated words into a stream of them.
 * Kept out of `shortcuts.ts` so the binder stays a plain module with no rune state of its own.
 */

const SHORTCUTS_KEY = 'lumia-shortcuts';

function readInitialEnabled(): boolean {
	if (typeof localStorage === 'undefined') return true;
	// Absent means never chosen, and the shortcuts are on by default.
	return localStorage.getItem(SHORTCUTS_KEY) !== 'off';
}

let enabled = $state<boolean>(readInitialEnabled());

export function areShortcutsEnabled(): boolean {
	return enabled;
}

export function setShortcutsEnabled(on: boolean): void {
	enabled = on;
	localStorage.setItem(SHORTCUTS_KEY, on ? 'on' : 'off');
}
