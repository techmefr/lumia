import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ShortcutsHelp from './shortcuts-help.svelte';
import {
	HELP_SHORTCUTS,
	NAVIGATION_SHORTCUTS,
	READING_SHORTCUTS
} from '$technical/keyboard/shortcut-catalogue';

const onClose = vi.fn();

function panel() {
	const { container, unmount } = render(ShortcutsHelp, { onClose } as never);
	return {
		container,
		unmount,
		root: () => container.querySelector('[data-test-shortcuts-help]')!,
		keys: () => [...container.querySelectorAll('kbd')].map((key) => key.textContent),
		close: () => container.querySelector<HTMLButtonElement>('[data-test-shortcuts-help-close]')!
	};
}

afterEach(() => {
	vi.clearAllMocks();
});

describe('what it announces', () => {
	it('is a modal dialog, so a screen reader stops reading the page behind it', () => {
		const view = panel();
		expect(view.root().getAttribute('role')).toBe('dialog');
		expect(view.root().getAttribute('aria-modal')).toBe('true');
	});

	it('takes the focus when it opens, rather than leaving it on the page behind', () => {
		const view = panel();
		expect(view.root().contains(document.activeElement)).toBe(true);
	});
});

describe('what it lists', () => {
	// The panel is generated from the catalogue precisely so the two can never disagree.
	it.each(NAVIGATION_SHORTCUTS)('lists the $id navigation shortcut', (shortcut) => {
		const view = panel();
		for (const key of shortcut.keys) expect(view.keys()).toContain(key);
	});

	it('lists every reading and general shortcut declared in the catalogue', () => {
		const view = panel();
		const listed = view.keys();
		for (const entry of [...READING_SHORTCUTS, ...HELP_SHORTCUTS]) {
			for (const key of entry.keys) expect(listed).toContain(key);
		}
	});

	it('points at the settings, so the off switch is findable from here', () => {
		const view = panel();
		const link = view.container.querySelector<HTMLAnchorElement>('a[href$="/settings"]');
		expect(link).not.toBeNull();
	});
});

describe('how it closes', () => {
	it('closes on Escape', async () => {
		panel();
		await fireEvent.keyDown(window, { key: 'Escape' });
		expect(onClose).toHaveBeenCalled();
	});

	it('closes on the close button', async () => {
		const view = panel();
		await fireEvent.click(view.close());
		expect(onClose).toHaveBeenCalled();
	});
});
