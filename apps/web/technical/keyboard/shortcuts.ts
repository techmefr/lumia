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
 * Binds single-key shortcuts on the document. Keys are matched on `event.key`, lowercased.
 * Returns the teardown function, so it can be returned straight from an $effect or onMount.
 */
export function bindShortcuts(handlers: ShortcutHandlers): () => void {
	function onKeydown(event: KeyboardEvent) {
		if (event.metaKey || event.ctrlKey || event.altKey) return;
		if (isTypingTarget(event.target)) return;

		const handler = handlers[event.key.toLowerCase()];
		if (!handler) return;
		event.preventDefault();
		handler();
	}

	document.addEventListener('keydown', onKeydown);
	return () => document.removeEventListener('keydown', onKeydown);
}
