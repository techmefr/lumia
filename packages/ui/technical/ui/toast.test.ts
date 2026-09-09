import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { toast, toasts } from './toast.svelte.js';

// The clock is the one thing mocked here: auto-dismiss is defined in milliseconds, and a test that
// really waited three seconds for it would be three seconds of suite time per case.
beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	// The store is a module singleton, so a toast left behind would be visible to the next test.
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.useRealTimers();
});

describe('showing a toast', () => {
	it('adds it to the list', () => {
		toast('Article marked as read');
		expect(toasts.toasts.map((item) => item.message)).toEqual(['Article marked as read']);
	});

	it('defaults to the neutral tone', () => {
		toast('Saved');
		expect(toasts.toasts[0].tone).toBe('default');
	});

	it('keeps the tone it was given', () => {
		toast('Deletion failed', { tone: 'destructive' });
		expect(toasts.toasts[0].tone).toBe('destructive');
	});

	it('carries no action unless one was passed', () => {
		toast('Saved');
		expect(toasts.toasts[0].action).toBeUndefined();
	});

	// Compared field by field rather than by identity: the store is `$state`, so what comes back is
	// a reactive proxy of the object that went in, not the object itself.
	it('carries the action it was given', () => {
		let undone = false;
		toast('Feed deleted', {
			action: {
				label: 'Undo',
				run: () => {
					undone = true;
				}
			}
		});

		expect(toasts.toasts[0].action?.label).toBe('Undo');
		toasts.toasts[0].action?.run();
		expect(undone).toBe(true);
	});

	it('returns the id of the toast it created', () => {
		const id = toast('Saved');
		expect(toasts.toasts[0].id).toBe(id);
	});

	it('gives each toast a distinct id, so dismissing one leaves the others', () => {
		const first = toast('First');
		const second = toast('Second');
		expect(first).not.toBe(second);

		toasts.dismiss(first);
		expect(toasts.toasts.map((item) => item.message)).toEqual(['Second']);
	});

	it('stacks several, oldest first', () => {
		toast('First');
		toast('Second');
		toast('Third');
		expect(toasts.toasts.map((item) => item.message)).toEqual(['First', 'Second', 'Third']);
	});
});

describe('auto-dismiss', () => {
	it('keeps a plain toast up for three seconds', () => {
		toast('Saved');
		vi.advanceTimersByTime(2999);
		expect(toasts.toasts).toHaveLength(1);

		vi.advanceTimersByTime(1);
		expect(toasts.toasts).toHaveLength(0);
	});

	// An action nobody has time to click is not an action. This is the reason the two durations
	// differ, so it gets its own case rather than being folded into the one above.
	it('keeps a toast carrying an action up for seven seconds', () => {
		toast('Feed deleted', { action: { label: 'Undo', run: () => {} } });
		vi.advanceTimersByTime(3000);
		expect(toasts.toasts).toHaveLength(1);

		vi.advanceTimersByTime(4000);
		expect(toasts.toasts).toHaveLength(0);
	});

	it('honours an explicit duration over both defaults', () => {
		toast('Slow', { duration: 500 });
		vi.advanceTimersByTime(499);
		expect(toasts.toasts).toHaveLength(1);

		vi.advanceTimersByTime(1);
		expect(toasts.toasts).toHaveLength(0);
	});

	it('honours an explicit duration even when an action is present', () => {
		toast('Feed deleted', { duration: 500, action: { label: 'Undo', run: () => {} } });
		vi.advanceTimersByTime(500);
		expect(toasts.toasts).toHaveLength(0);
	});

	it('dismisses each toast on its own schedule', () => {
		toast('Short', { duration: 1000 });
		toast('Long', { duration: 5000 });

		vi.advanceTimersByTime(1000);
		expect(toasts.toasts.map((item) => item.message)).toEqual(['Long']);

		vi.advanceTimersByTime(4000);
		expect(toasts.toasts).toHaveLength(0);
	});

	// The timer for a toast dismissed by hand still fires. If it matched on anything but the id it
	// would take an unrelated toast down with it.
	it('leaves the others alone when a timer fires after a manual dismiss', () => {
		const first = toast('First', { duration: 1000 });
		toast('Second', { duration: 5000 });

		toasts.dismiss(first);
		vi.advanceTimersByTime(1000);

		expect(toasts.toasts.map((item) => item.message)).toEqual(['Second']);
	});
});

describe('dismissing by hand', () => {
	it('removes only the toast asked for', () => {
		const first = toast('First');
		toast('Second');

		toasts.dismiss(first);

		expect(toasts.toasts.map((item) => item.message)).toEqual(['Second']);
	});

	it('does nothing for an id that is not there', () => {
		toast('Saved');
		toasts.dismiss(-1);
		expect(toasts.toasts).toHaveLength(1);
	});

	it('is safe to call twice on the same id', () => {
		const id = toast('Saved');
		toasts.dismiss(id);
		toasts.dismiss(id);
		expect(toasts.toasts).toHaveLength(0);
	});
});
