import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Toaster from './toaster.svelte';
import { toast, toasts } from './toast.svelte.js';

type Props = Parameters<typeof Toaster>[1];

function toaster(props: Partial<Props> = {}) {
	const { container } = render(Toaster, props as Props);
	return {
		region: container.querySelector('[data-test-toast-region]')!,
		items: () => [...container.querySelectorAll('[data-test-toast]')],
		messages: () =>
			[...container.querySelectorAll('[data-test-toast-message]')].map((node) =>
				node.textContent?.trim()
			),
		action: () => container.querySelector<HTMLButtonElement>('[data-test-toast-action]'),
		close: () => container.querySelector<HTMLButtonElement>('[data-test-toast-close]')!
	};
}

afterEach(() => {
	// The store is a module singleton shared with every other test in the file.
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
});

describe('the live region', () => {
	// The region has to be in the document *before* a message lands in it: a container that appears
	// at the same time as its first child is not announced by most screen readers.
	it('exists while there is nothing to show', () => {
		const { region, items } = toaster();
		expect(region).not.toBeNull();
		expect(items()).toHaveLength(0);
	});

	it('is polite, so a toast never interrupts what is being read', () => {
		expect(toaster().region.getAttribute('aria-live')).toBe('polite');
	});

	// Each toast is a message of its own; atomic would make every insertion re-announce the whole
	// stack.
	it('announces additions rather than the whole stack', () => {
		expect(toaster().region.getAttribute('aria-atomic')).toBe('false');
	});
});

describe('what it renders', () => {
	it('shows a toast added to the store', async () => {
		const view = toaster();
		toast('Article marked as read');
		await vi.waitFor(() => expect(view.messages()).toEqual(['Article marked as read']));
	});

	it('shows several, oldest first', async () => {
		const view = toaster();
		toast('First');
		toast('Second');
		await vi.waitFor(() => expect(view.messages()).toEqual(['First', 'Second']));
	});

	it('marks the tone, so a failure does not look like a confirmation', async () => {
		const view = toaster();
		toast('Deletion failed', { tone: 'destructive' });
		await vi.waitFor(() =>
			expect(view.items()[0]?.getAttribute('data-test-tone')).toBe('destructive')
		);
	});

	it('renders no action button when the toast carries none', async () => {
		const view = toaster();
		toast('Saved');
		await vi.waitFor(() => expect(view.items()).toHaveLength(1));
		expect(view.action()).toBeNull();
	});

	it('labels the action with the label the caller gave', async () => {
		const view = toaster();
		toast('Feed deleted', { action: { label: 'Undo', run: () => {} } });
		await vi.waitFor(() => expect(view.action()?.textContent?.trim()).toBe('Undo'));
	});
});

describe('dismissing', () => {
	it('removes the toast when the close button is pressed', async () => {
		const view = toaster();
		toast('Saved');
		await vi.waitFor(() => expect(view.items()).toHaveLength(1));

		await fireEvent.click(view.close());

		expect(toasts.toasts).toHaveLength(0);
	});

	it('runs the action and dismisses in one press', async () => {
		let undone = false;
		const view = toaster();
		toast('Feed deleted', {
			action: {
				label: 'Undo',
				run: () => {
					undone = true;
				}
			}
		});
		await vi.waitFor(() => expect(view.action()).not.toBeNull());

		await fireEvent.click(view.action()!);

		expect(undone).toBe(true);
		expect(toasts.toasts).toHaveLength(0);
	});

	// An async undo — the usual case, since it re-posts to the api — must not leave the toast up
	// waiting for the round trip, nor swallow the press.
	it('does not wait for an async action to settle before dismissing', async () => {
		let started = false;
		const view = toaster();
		toast('Feed deleted', {
			action: {
				label: 'Undo',
				run: async () => {
					started = true;
					await new Promise((resolve) => setTimeout(resolve, 0));
				}
			}
		});
		await vi.waitFor(() => expect(view.action()).not.toBeNull());

		await fireEvent.click(view.action()!);

		expect(started).toBe(true);
		expect(toasts.toasts).toHaveLength(0);
	});

	it('dismisses only the toast whose button was pressed', async () => {
		const view = toaster();
		toast('First');
		toast('Second');
		await vi.waitFor(() => expect(view.items()).toHaveLength(2));

		await fireEvent.click(view.close());

		expect(toasts.toasts.map((item) => item.message)).toEqual(['Second']);
	});
});

describe('the close label', () => {
	it('falls back to an english default', async () => {
		const view = toaster();
		toast('Saved');
		await vi.waitFor(() => expect(view.items()).toHaveLength(1));
		expect(view.close().getAttribute('aria-label')).toBe('Dismiss notification');
	});

	it('uses the label the app passes in', async () => {
		const view = toaster({ closeLabel: 'Fermer la notification' });
		toast('Saved');
		await vi.waitFor(() => expect(view.items()).toHaveLength(1));
		expect(view.close().getAttribute('aria-label')).toBe('Fermer la notification');
	});
});
