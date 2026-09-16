import { fireEvent, render } from '@testing-library/svelte';
import Star from '@lucide/svelte/icons/star';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OrbitButton, { type OrbitAction } from './orbit-button.svelte';

const favorite = vi.fn();
const share = vi.fn();
const listen = vi.fn();

function actions(overrides: Partial<OrbitAction>[] = []): OrbitAction[] {
	const base: OrbitAction[] = [
		{ id: 'favorite', label: 'Favoris', icon: Star, active: false, run: favorite },
		{ id: 'listen', label: 'Écouter', icon: Star, active: false, run: listen },
		{ id: 'share', label: 'Partager', icon: Star, run: share }
	];
	return base.map((action, index) => ({ ...action, ...overrides[index] }));
}

function widget(position: 'left' | 'right' = 'right', list = actions()) {
	const { container, unmount } = render(OrbitButton, { position, actions: list } as never);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		unmount,
		root: () => q('[data-test-orbit]')!,
		toggle: () => q<HTMLButtonElement>('[data-test-orbit-toggle]')!,
		menu: () => q('[data-test-orbit-menu]'),
		items: () => [...container.querySelectorAll<HTMLButtonElement>('[data-test-orbit-action]')],
		item: (id: string) => q<HTMLButtonElement>(`[data-test-orbit-action="${id}"]`)
	};
}

async function opened(position: 'left' | 'right' = 'right', list = actions()) {
	const view = widget(position, list);
	await fireEvent.click(view.toggle());
	await vi.waitFor(() => expect(view.menu()).not.toBeNull());
	return view;
}

afterEach(() => {
	vi.clearAllMocks();
});

describe('where it sits', () => {
	// The whole point of the stored preference: the button has to move to the thumb's side.
	it.each(['left', 'right'] as const)('honours a stored position of %p', async (position) => {
		const view = widget(position);

		expect(view.root().getAttribute('data-position')).toBe(position);
		expect(view.root().className).toContain(`${position}-4`);
	});

	// It floats over the article, above a bottom navigation whose height is a variable: a fixed
	// offset would put it on top of the navigation on a phone.
	it('clears the bottom navigation rather than overlapping it', () => {
		const view = widget();

		expect(view.root().getAttribute('style')).toContain('var(--bottom-nav-h');
	});
});

describe('opening and closing', () => {
	it('starts closed, with nothing floating over the article', () => {
		const view = widget();

		expect(view.menu()).toBeNull();
		expect(view.toggle().getAttribute('aria-expanded')).toBe('false');
	});

	it('opens on a press and says so', async () => {
		const view = await opened();

		expect(view.toggle().getAttribute('aria-expanded')).toBe('true');
		expect(view.items()).toHaveLength(3);
	});

	it('closes again on a second press', async () => {
		const view = await opened();

		await fireEvent.click(view.toggle());

		expect(view.menu()).toBeNull();
	});

	it('closes when something outside it is pressed', async () => {
		const view = await opened();

		await fireEvent.pointerDown(document.body);

		await vi.waitFor(() => expect(view.menu()).toBeNull());
	});

	it('stays open when the press is inside it', async () => {
		const view = await opened();

		await fireEvent.pointerDown(view.item('share')!);

		expect(view.menu()).not.toBeNull();
	});

	// A listener left on the document keeps closing a menu that is no longer on screen.
	it('stops listening once the page it is on is gone', async () => {
		const view = await opened();

		view.unmount();

		expect(() => fireEvent.pointerDown(document.body)).not.toThrow();
	});
});

describe('reaching it with a keyboard', () => {
	// Without this the orbit is a gesture-only control, which is exactly what the reading screen
	// was already faulted for.
	it('moves focus into the menu when it opens', async () => {
		const view = await opened();

		expect(document.activeElement).toBe(view.item('favorite'));
	});

	it('walks down the actions with the down arrow', async () => {
		const view = await opened();

		await fireEvent.keyDown(view.menu()!, { key: 'ArrowDown' });

		expect(document.activeElement).toBe(view.item('listen'));
	});

	it('walks back up with the up arrow', async () => {
		const view = await opened();
		await fireEvent.keyDown(view.menu()!, { key: 'ArrowDown' });

		await fireEvent.keyDown(view.menu()!, { key: 'ArrowUp' });

		expect(document.activeElement).toBe(view.item('favorite'));
	});

	// Holding an arrow at an edge would otherwise look like the menu had stopped responding.
	it('wraps from the last action back to the first', async () => {
		const view = await opened();
		await fireEvent.keyDown(view.menu()!, { key: 'End' });
		expect(document.activeElement).toBe(view.item('share'));

		await fireEvent.keyDown(view.menu()!, { key: 'ArrowDown' });

		expect(document.activeElement).toBe(view.item('favorite'));
	});

	it('jumps to the first and last actions with home and end', async () => {
		const view = await opened();

		await fireEvent.keyDown(view.menu()!, { key: 'End' });
		expect(document.activeElement).toBe(view.item('share'));

		await fireEvent.keyDown(view.menu()!, { key: 'Home' });
		expect(document.activeElement).toBe(view.item('favorite'));
	});

	it('opens on the first action when the trigger gets a down arrow', async () => {
		const view = widget();

		await fireEvent.keyDown(view.toggle(), { key: 'ArrowDown' });

		await vi.waitFor(() => expect(document.activeElement).toBe(view.item('favorite')));
	});

	it('opens on the last action when the trigger gets an up arrow', async () => {
		const view = widget();

		await fireEvent.keyDown(view.toggle(), { key: 'ArrowUp' });

		await vi.waitFor(() => expect(document.activeElement).toBe(view.item('share')));
	});

	// Escape has to give focus back, otherwise it lands on the body and tabbing restarts at the
	// top of the article.
	it('closes on escape and puts focus back on the button', async () => {
		const view = await opened();

		await fireEvent.keyDown(view.menu()!, { key: 'Escape' });

		expect(view.menu()).toBeNull();
		expect(document.activeElement).toBe(view.toggle());
	});
});

describe('how it is announced', () => {
	it('is a menu button', async () => {
		const view = widget();

		expect(view.toggle().getAttribute('aria-haspopup')).toBe('menu');
		await fireEvent.click(view.toggle());
		expect(view.menu()!.getAttribute('role')).toBe('menu');
		expect(view.menu()!.getAttribute('aria-label')).not.toBeNull();
	});

	// The icon is the only visible content of the trigger, so the name has to come from the label.
	it('names the trigger, and the name follows the open state', async () => {
		const view = widget();
		const closedLabel = view.toggle().getAttribute('aria-label');
		expect(closedLabel).not.toBeNull();

		await fireEvent.click(view.toggle());

		expect(view.toggle().getAttribute('aria-label')).not.toBe(closedLabel);
	});

	// Favourite and listen are on/off, share is a one-shot: announcing them alike would tell a
	// screen reader that sharing can be switched off.
	it('marks the toggles as checkable and the one-shots as plain commands', async () => {
		const view = await opened('right', actions([{ active: true }]));

		expect(view.item('favorite')!.getAttribute('role')).toBe('menuitemcheckbox');
		expect(view.item('favorite')!.getAttribute('aria-checked')).toBe('true');
		expect(view.item('listen')!.getAttribute('aria-checked')).toBe('false');
		expect(view.item('share')!.getAttribute('role')).toBe('menuitem');
		expect(view.item('share')!.getAttribute('aria-checked')).toBeNull();
	});

	it('labels every action in words, not by its icon alone', async () => {
		const view = await opened();

		expect(view.item('favorite')!.textContent).toContain('Favoris');
		expect(view.item('share')!.textContent).toContain('Partager');
	});

	// Roving tabindex: the menu owns arrow navigation, so the items must stay out of the tab order.
	it('keeps the actions out of the tab sequence', async () => {
		const view = await opened();

		for (const item of view.items()) expect(item.getAttribute('tabindex')).toBe('-1');
	});
});

describe('running an action', () => {
	it('runs the one that was pressed', async () => {
		const view = await opened();

		await fireEvent.click(view.item('share')!);

		expect(share).toHaveBeenCalledTimes(1);
		expect(favorite).not.toHaveBeenCalled();
	});

	// A menu that stayed open would cover the paragraph the reader just came back to.
	it('closes and hands focus back to the button', async () => {
		const view = await opened();

		await fireEvent.click(view.item('favorite')!);

		expect(view.menu()).toBeNull();
		expect(document.activeElement).toBe(view.toggle());
	});

	it('shows only the actions it was given', async () => {
		const view = await opened('right', [
			{ id: 'share', label: 'Partager', icon: Star, run: share }
		]);

		expect(view.items()).toHaveLength(1);
		expect(view.item('listen')).toBeNull();
	});
});
