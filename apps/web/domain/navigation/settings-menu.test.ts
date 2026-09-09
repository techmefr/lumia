import Settings from '@lucide/svelte/icons/settings';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SettingsMenu from './settings-menu.svelte';

type Props = Parameters<typeof SettingsMenu>[1];

const LONG_PRESS_MS = 450;

function menu(overrides: Partial<Props> = {}) {
	const run = vi.fn();
	const { container, unmount } = render(SettingsMenu, {
		entries: [
			{ label: 'Apparence', href: '/settings/appearance' },
			{ label: 'Se déconnecter', run }
		],
		href: '/settings',
		label: 'Réglages',
		icon: Settings,
		...overrides
	} as Props);

	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		unmount,
		run,
		link: () => q<HTMLAnchorElement>('[data-test-menu-link]')!,
		toggle: () => q<HTMLButtonElement>('[data-test-menu-toggle]')!,
		menu: () => q('[data-test-menu]'),
		entries: () => [...container.querySelectorAll<HTMLElement>('[data-test-menu-entry]')],
		entry: (label: string) => q<HTMLElement>(`[data-test-menu-entry="${label}"]`)!
	};
}

beforeEach(() => {
	vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
	vi.useRealTimers();
});

describe('the short press', () => {
	it('is a real link to the page itself', () => {
		const view = menu();
		expect(view.link().getAttribute('href')).toBe('/settings');
	});

	it('is named for a screen reader, since it only shows an icon', () => {
		expect(menu().link().getAttribute('aria-label')).toBe('Réglages');
	});

	it('opens nothing on its own', async () => {
		const view = menu();

		await fireEvent.pointerDown(view.link());
		await fireEvent.pointerUp(view.link());

		expect(view.menu()).toBeNull();
	});

	it('lets the navigation happen', async () => {
		const view = menu();
		await fireEvent.pointerDown(view.link());
		await fireEvent.pointerUp(view.link());

		const click = new MouseEvent('click', { bubbles: true, cancelable: true });
		view.link().dispatchEvent(click);

		expect(click.defaultPrevented).toBe(false);
	});
});

describe('the long press', () => {
	it('opens the menu once it is held long enough', async () => {
		const view = menu();

		await fireEvent.pointerDown(view.link());
		vi.advanceTimersByTime(LONG_PRESS_MS);
		await Promise.resolve();

		expect(view.menu()).not.toBeNull();
	});

	it('opens nothing before that', async () => {
		const view = menu();

		await fireEvent.pointerDown(view.link());
		vi.advanceTimersByTime(LONG_PRESS_MS - 1);
		await Promise.resolve();

		expect(view.menu()).toBeNull();
	});

	// The press is on a link, so the browser will navigate on release. Swallowing that click is
	// what keeps a long press from opening the menu and leaving the page at the same time.
	it('does not navigate away after it opened the menu', async () => {
		const view = menu();

		await fireEvent.pointerDown(view.link());
		vi.advanceTimersByTime(LONG_PRESS_MS);
		await Promise.resolve();
		await fireEvent.pointerUp(view.link());

		const click = new MouseEvent('click', { bubbles: true, cancelable: true });
		view.link().dispatchEvent(click);

		expect(click.defaultPrevented).toBe(true);
	});

	it('navigates normally on the press after that', async () => {
		const view = menu();
		await fireEvent.pointerDown(view.link());
		vi.advanceTimersByTime(LONG_PRESS_MS);
		await Promise.resolve();
		await fireEvent.pointerUp(view.link());
		view.link().dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));

		const second = new MouseEvent('click', { bubbles: true, cancelable: true });
		view.link().dispatchEvent(second);

		expect(second.defaultPrevented).toBe(false);
	});

	it('opens nothing when the finger lifts in time', async () => {
		const view = menu();

		await fireEvent.pointerDown(view.link());
		vi.advanceTimersByTime(200);
		await fireEvent.pointerUp(view.link());
		vi.advanceTimersByTime(LONG_PRESS_MS);
		await Promise.resolve();

		expect(view.menu()).toBeNull();
	});

	// A finger that slides off the button is not a long press: without this, dragging the page
	// from the toolbar pops the menu open.
	it('opens nothing when the finger slides off', async () => {
		const view = menu();

		await fireEvent.pointerDown(view.link());
		await fireEvent.pointerLeave(view.link());
		vi.advanceTimersByTime(LONG_PRESS_MS);
		await Promise.resolve();

		expect(view.menu()).toBeNull();
	});

	it('opens nothing when the gesture is cancelled', async () => {
		const view = menu();

		await fireEvent.pointerDown(view.link());
		await fireEvent.pointerCancel(view.link());
		vi.advanceTimersByTime(LONG_PRESS_MS);
		await Promise.resolve();

		expect(view.menu()).toBeNull();
	});

	// The browser's own context menu on a long press would cover ours.
	it('keeps the browser context menu out of the way', async () => {
		const view = menu();

		const contextMenu = new MouseEvent('contextmenu', { bubbles: true, cancelable: true });
		view.link().dispatchEvent(contextMenu);

		expect(contextMenu.defaultPrevented).toBe(true);
	});
});

describe('the explicit toggle', () => {
	// A long press is undiscoverable and unreachable from a keyboard, so the arrow next to the link
	// is not a nicety: it is the only accessible way into the menu.
	it('opens the menu', async () => {
		const view = menu();

		await fireEvent.click(view.toggle());

		expect(view.menu()).not.toBeNull();
	});

	it('closes it again', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.click(view.toggle());

		expect(view.menu()).toBeNull();
	});

	it('says what it does and what it controls', () => {
		const view = menu();
		expect(view.toggle().getAttribute('aria-haspopup')).toBe('menu');
		expect(view.toggle().getAttribute('aria-expanded')).toBe('false');
		expect(view.toggle().getAttribute('aria-label')).toContain('Réglages');
	});

	it('reports the menu as open once it is', async () => {
		const view = menu();

		await fireEvent.click(view.toggle());

		expect(view.toggle().getAttribute('aria-expanded')).toBe('true');
	});

	it('is big enough to hit with a thumb', () => {
		expect(menu().toggle().className).toContain('min-h-9');
	});
});

describe('the entries', () => {
	it('lists them all', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		expect(view.entries()).toHaveLength(2);
	});

	it('marks the container and its items for assistive technology', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		expect(view.menu()?.getAttribute('role')).toBe('menu');
		for (const entry of view.entries()) expect(entry.getAttribute('role')).toBe('menuitem');
	});

	it('renders an entry with a destination as a link', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		expect(view.entry('Apparence').tagName).toBe('A');
		expect(view.entry('Apparence').getAttribute('href')).toBe('/settings/appearance');
	});

	it('renders an entry with an action as a button', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		expect(view.entry('Se déconnecter').tagName).toBe('BUTTON');
	});

	it('runs the action it was given', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.click(view.entry('Se déconnecter'));

		expect(view.run).toHaveBeenCalledTimes(1);
	});

	it('closes after an action', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.click(view.entry('Se déconnecter'));

		expect(view.menu()).toBeNull();
	});

	it('closes when a destination is chosen', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.click(view.entry('Apparence'));

		expect(view.menu()).toBeNull();
	});

	it('renders an empty menu rather than nothing when there is no entry', async () => {
		const view = menu({ entries: [] });
		await fireEvent.click(view.toggle());

		expect(view.menu()).not.toBeNull();
		expect(view.entries()).toHaveLength(0);
	});
});

describe('dismissing the menu', () => {
	it('closes on a press outside it', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.pointerDown(document.body);

		expect(view.menu()).toBeNull();
	});

	it('stays open on a press inside it', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.pointerDown(view.entry('Apparence'));

		expect(view.menu()).not.toBeNull();
	});

	it('closes on escape', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.keyDown(document, { key: 'Escape' });

		expect(view.menu()).toBeNull();
	});

	it('ignores any other key', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		await fireEvent.keyDown(document, { key: 'a' });

		expect(view.menu()).not.toBeNull();
	});

	// Two listeners on the document, left behind on every navigation away from a page holding this
	// menu.
	it('stops listening once the page it is on is gone', async () => {
		const view = menu();
		await fireEvent.click(view.toggle());

		view.unmount();

		expect(() => fireEvent.keyDown(document, { key: 'Escape' })).not.toThrow();
		expect(() => fireEvent.pointerDown(document.body)).not.toThrow();
	});
});
