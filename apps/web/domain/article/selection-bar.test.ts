import { render, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SelectionBar from './selection-bar.svelte';

type Props = Parameters<typeof SelectionBar>[1];

const PLAYLISTS = [
	{ id: 'playlist-1', name: 'Trajet', item_count: 0, total_reading_minutes: 0 },
	{ id: 'playlist-2', name: 'Soir', item_count: 2, total_reading_minutes: 9 }
];

function bar(props: Partial<Props> = {}) {
	const handlers = {
		onMarkRead: vi.fn(),
		onMarkUnread: vi.fn(),
		onSave: vi.fn(),
		onUnsave: vi.fn(),
		onFavorite: vi.fn(),
		onUnfavorite: vi.fn(),
		onAddToPlaylist: vi.fn(),
		onSelectAll: vi.fn(),
		onClose: vi.fn()
	};
	const { container } = render(SelectionBar, {
		count: 3,
		loadedCount: 24,
		playlists: PLAYLISTS,
		...handlers,
		...props
	} as Props);

	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		handlers,
		root: () => q('[data-test-selection-bar]'),
		count: () => q('[data-test-selection-count]'),
		markRead: () => q<HTMLButtonElement>('[data-test-selection-read]'),
		markUnread: () => q<HTMLButtonElement>('[data-test-selection-unread]'),
		save: () => q<HTMLButtonElement>('[data-test-selection-save]'),
		favorite: () => q<HTMLButtonElement>('[data-test-selection-favorite]'),
		playlist: () => q<HTMLSelectElement>('[data-test-selection-playlist]'),
		playlistAdd: () => q<HTMLButtonElement>('[data-test-selection-playlist-add]'),
		selectAll: () => q<HTMLButtonElement>('[data-test-selection-all]'),
		close: () => q<HTMLButtonElement>('[data-test-selection-close]')
	};
}

describe('saying what is selected', () => {
	// A bulk action is only safe if the reader can see how far it reaches before pressing anything.
	it('spells out how many articles are concerned', () => {
		expect(bar({ count: 3 }).count()?.textContent?.trim()).toBe('3 article(s) selected');
	});

	it('announces the count politely, so a screen reader follows the selection changing', () => {
		const view = bar();
		expect(view.count()?.getAttribute('role')).toBe('status');
		expect(view.count()?.getAttribute('aria-live')).toBe('polite');
	});

	it('names the bar itself, so it is reachable as a landmark', () => {
		expect(bar().root()?.getAttribute('aria-label')).toBe('Bulk actions');
	});

	it('says how many articles a select-all would take, never more than are loaded', () => {
		expect(bar({ loadedCount: 24 }).selectAll()?.textContent?.trim()).toBe('Select all (24)');
	});
});

describe('with nothing selected', () => {
	it('says so rather than showing a bare zero', () => {
		expect(bar({ count: 0 }).count()?.textContent?.trim()).toBe('No article selected');
	});

	it('disables every action, since none of them has a target', () => {
		const view = bar({ count: 0 });
		expect(view.markRead()?.disabled).toBe(true);
		expect(view.save()?.disabled).toBe(true);
		expect(view.favorite()?.disabled).toBe(true);
	});

	it('still lets the reader select everything or leave', () => {
		const view = bar({ count: 0 });
		expect(view.selectAll()?.disabled).toBe(false);
		expect(view.close()?.disabled).toBe(false);
	});
});

describe('running an action', () => {
	it.each([
		['markRead', 'onMarkRead'],
		['markUnread', 'onMarkUnread'],
		['save', 'onSave'],
		['favorite', 'onFavorite']
	] as const)('%s asks for exactly that axis', async (control, handler) => {
		const view = bar();
		await fireEvent.click(view[control]() as HTMLButtonElement);
		expect(view.handlers[handler]).toHaveBeenCalledOnce();
	});

	// Two requests over the same selection would race, and the second undo would revert the wrong
	// set of ids.
	it('locks the actions while one is already running', () => {
		const view = bar({ busy: true });
		expect(view.markRead()?.disabled).toBe(true);
	});
});

describe('adding to a playlist', () => {
	it('waits for a playlist to be chosen before offering to add', () => {
		expect(bar().playlistAdd()?.disabled).toBe(true);
	});

	it('hands over the chosen playlist', async () => {
		const view = bar();
		await fireEvent.change(view.playlist() as HTMLSelectElement, {
			target: { value: 'playlist-2' }
		});
		await fireEvent.click(view.playlistAdd() as HTMLButtonElement);
		expect(view.handlers.onAddToPlaylist).toHaveBeenCalledWith('playlist-2');
	});

	it('leaves the control out entirely when there is no playlist to add to', () => {
		expect(bar({ playlists: [] }).playlist()).toBeNull();
	});

	it('labels the playlist control for a screen reader', () => {
		const view = bar();
		const label = view.container.querySelector(`label[for="${view.playlist()?.id}"]`);
		expect(label?.textContent).toBe('Target playlist');
	});
});

describe('leaving', () => {
	it('closes on demand', async () => {
		const view = bar();
		await fireEvent.click(view.close() as HTMLButtonElement);
		expect(view.handlers.onClose).toHaveBeenCalledOnce();
	});
});
