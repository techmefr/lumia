import { areShortcutsEnabled } from './shortcuts-store.svelte.js';

export type ShortcutHandlers = Record<string, () => void>;

/** Typing in a field must never trigger a shortcut, so those targets are skipped entirely. */
function isTypingTarget(target: EventTarget | null): boolean {
	if (!(target instanceof HTMLElement)) return false;
	// Both forms, because neither covers the other on its own: `isContentEditable` is inherited from
	// an ancestor but is absent outside a real browser, and the attribute is the html contract
	// itself. `closest` walks up, so typing inside a `<b>` nested in an editable region counts too.
	if (target.isContentEditable || target.closest('[contenteditable="true"]') !== null) return true;
	return ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName);
}

/**
 * A dialog or a menu owns the keyboard while it is up: its own arrows, Escape and Tab are the only
 * thing that should answer. Presence in the dom is the test because every such surface here is
 * rendered only while open.
 */
function isOverlayOpen(): boolean {
	return document.querySelector('[role="dialog"], [role="menu"]') !== null;
}

function isIgnored(event: KeyboardEvent): boolean {
	if (event.metaKey || event.ctrlKey || event.altKey) return true;
	if (!areShortcutsEnabled()) return true;
	if (isTypingTarget(event.target)) return true;
	return isOverlayOpen();
}

/**
 * Binds single-key shortcuts on the document. Keys are matched on `event.key`, lowercased.
 * Returns the teardown function, so it can be returned straight from an $effect or onMount.
 */
export function bindShortcuts(handlers: ShortcutHandlers): () => void {
	function onKeydown(event: KeyboardEvent) {
		if (isIgnored(event)) return;

		const handler = handlers[event.key.toLowerCase()];
		if (!handler) return;
		event.preventDefault();
		handler();
	}

	document.addEventListener('keydown', onKeydown);
	return () => document.removeEventListener('keydown', onKeydown);
}

/** How long a prefix stays armed. Long enough to be typed deliberately, short enough that a stray
 * `g` does not turn the next unrelated keypress into a jump. */
const SEQUENCE_TIMEOUT_MS = 1500;

/**
 * Binds two-key sequences: the prefix arms the binding, the next key runs the handler. Any other
 * key, or the timeout, disarms it and is otherwise left alone.
 */
export function bindSequenceShortcuts(prefix: string, handlers: ShortcutHandlers): () => void {
	let armed = false;
	let timer: ReturnType<typeof setTimeout> | null = null;

	function disarm() {
		armed = false;
		if (timer !== null) clearTimeout(timer);
		timer = null;
	}

	function onKeydown(event: KeyboardEvent) {
		if (isIgnored(event)) {
			disarm();
			return;
		}

		const key = event.key.toLowerCase();

		if (!armed) {
			if (key !== prefix) return;
			armed = true;
			event.preventDefault();
			timer = setTimeout(disarm, SEQUENCE_TIMEOUT_MS);
			return;
		}

		disarm();
		const handler = handlers[key];
		if (!handler) return;
		event.preventDefault();
		handler();
	}

	document.addEventListener('keydown', onKeydown);
	return () => {
		disarm();
		document.removeEventListener('keydown', onKeydown);
	};
}
