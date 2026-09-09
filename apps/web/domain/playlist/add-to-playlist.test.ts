import type { PlaylistSummary } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import AddToPlaylist from './add-to-playlist.svelte';

// The client is the app's http boundary, so it is what gets replaced.
vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		playlist: {
			listPlaylists: vi.fn(),
			addArticle: vi.fn(),
			createPlaylist: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.playlist);

function playlist(id: string, name: string, itemCount = 3): PlaylistSummary {
	return { id, name, item_count: itemCount, total_minutes: itemCount * 4 } as PlaylistSummary;
}

const PLAYLISTS = [playlist('p1', 'Matin'), playlist('p2', 'Trajet', 7)];

function widget() {
	const { container } = render(AddToPlaylist, { articleId: 'article-1' } as never);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		open: () => q<HTMLButtonElement>('[data-test-add-to-playlist]')!,
		panel: () => q('[data-test-playlist-panel]'),
		loading: () => q('[data-test-playlist-loading]'),
		empty: () => q('[data-test-playlist-empty]'),
		options: () => [...container.querySelectorAll<HTMLElement>('[data-test-playlist-option]')],
		option: (id: string) => q<HTMLButtonElement>(`[data-test-playlist-option="${id}"]`),
		newName: () => q<HTMLInputElement>('[data-test-input]')!,
		create: () => q<HTMLButtonElement>('[data-test-create-playlist]')!
	};
}

async function opened() {
	const view = widget();
	await fireEvent.click(view.open());
	await vi.waitFor(() => expect(view.panel()).not.toBeNull());
	return view;
}

beforeEach(() => {
	api.listPlaylists.mockResolvedValue(PLAYLISTS);
	api.addArticle.mockResolvedValue(undefined as never);
	api.createPlaylist.mockReset();
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.clearAllMocks();
});

describe('the panel', () => {
	// Nothing is fetched until the reader asks: the button sits on every article page, and loading
	// the playlists on mount would be one request per article opened, for a panel rarely used.
	it('is closed to start with, and has asked for nothing', () => {
		const view = widget();
		expect(view.panel()).toBeNull();
		expect(api.listPlaylists).not.toHaveBeenCalled();
	});

	it('says whether it is open', async () => {
		const view = widget();
		expect(view.open().getAttribute('aria-expanded')).toBe('false');

		await fireEvent.click(view.open());

		expect(view.open().getAttribute('aria-expanded')).toBe('true');
	});

	it('loads the playlists when it opens', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.options()).toHaveLength(2));
	});

	it('closes again on a second press', async () => {
		const view = await opened();

		await fireEvent.click(view.open());

		expect(view.panel()).toBeNull();
	});

	// Reopening must not re-fetch a list that has not changed, which is the common case: open,
	// hesitate, close, open again.
	it('does not reload a list it already has', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.options()).toHaveLength(2));

		await fireEvent.click(view.open());
		await fireEvent.click(view.open());

		expect(api.listPlaylists).toHaveBeenCalledTimes(1);
	});

	it('announces the wait while it loads', async () => {
		api.listPlaylists.mockReturnValue(new Promise(() => {}));
		const view = await opened();

		expect(view.loading()?.getAttribute('role')).toBe('status');
	});

	it('offers to create one when there is no playlist yet', async () => {
		api.listPlaylists.mockResolvedValue([]);
		const view = await opened();

		await vi.waitFor(() => expect(view.empty()).not.toBeNull());
		expect(view.create()).not.toBeNull();
	});

	it('says so when the playlists could not be loaded', async () => {
		api.listPlaylists.mockRejectedValue(new Error('offline'));
		await opened();

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
	});
});

describe('what each playlist shows', () => {
	it('names it', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.option('p1')?.textContent).toContain('Matin'));
	});

	// The count is what tells a playlist apart from an empty one with a similar name.
	it('shows how many articles it already holds', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.option('p2')?.textContent).toContain('7'));
	});

	it('makes every entry a real button', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.options()).toHaveLength(2));

		for (const option of view.options()) expect(option.tagName).toBe('BUTTON');
	});
});

describe('adding the article', () => {
	it('adds it to the playlist that was pressed', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.option('p2')).not.toBeNull());

		await fireEvent.click(view.option('p2')!);

		expect(api.addArticle).toHaveBeenCalledWith('p2', 'article-1');
	});

	it('closes the panel and confirms', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.option('p1')).not.toBeNull());

		await fireEvent.click(view.option('p1')!);

		await vi.waitFor(() => expect(view.panel()).toBeNull());
		expect(toasts.toasts[0].tone).toBe('default');
	});

	// The panel stays open on failure so the press can be repeated, and the toast says the article
	// did not go anywhere. Closing it silently would look like it worked.
	it('keeps the panel open and says so when it failed', async () => {
		api.addArticle.mockRejectedValue(new Error('offline'));
		const view = await opened();
		await vi.waitFor(() => expect(view.option('p1')).not.toBeNull());

		await fireEvent.click(view.option('p1')!);

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
		expect(view.panel()).not.toBeNull();
	});
});

describe('creating a playlist on the spot', () => {
	it('creates it and puts the article in it, in one press', async () => {
		api.createPlaylist.mockResolvedValue(playlist('p3', 'Soir', 0));
		const view = await opened();

		await fireEvent.input(view.newName(), { target: { value: 'Soir' } });
		await fireEvent.click(view.create());

		await vi.waitFor(() => expect(api.createPlaylist).toHaveBeenCalledWith('Soir'));
		expect(api.addArticle).toHaveBeenCalledWith('p3', 'article-1');
	});

	it('trims the name', async () => {
		api.createPlaylist.mockResolvedValue(playlist('p3', 'Soir', 0));
		const view = await opened();

		await fireEvent.input(view.newName(), { target: { value: '  Soir  ' } });
		await fireEvent.click(view.create());

		await vi.waitFor(() => expect(api.createPlaylist).toHaveBeenCalledWith('Soir'));
	});

	it.each(['', '   '])('creates nothing for a name of %p', async (value) => {
		const view = await opened();

		await fireEvent.input(view.newName(), { target: { value } });
		await fireEvent.click(view.create());

		expect(api.createPlaylist).not.toHaveBeenCalled();
	});

	it('closes the panel and clears the field', async () => {
		api.createPlaylist.mockResolvedValue(playlist('p3', 'Soir', 0));
		const view = await opened();

		await fireEvent.input(view.newName(), { target: { value: 'Soir' } });
		await fireEvent.click(view.create());

		await vi.waitFor(() => expect(view.panel()).toBeNull());
		await fireEvent.click(view.open());
		expect(view.newName().value).toBe('');
	});

	// Creating the playlist but failing to add the article is a half-done job, and the reader has
	// to know: otherwise the playlist appears, empty, with no explanation.
	it('says so when the article could not be added to the playlist it just created', async () => {
		api.createPlaylist.mockResolvedValue(playlist('p3', 'Soir', 0));
		api.addArticle.mockRejectedValue(new Error('offline'));
		const view = await opened();

		await fireEvent.input(view.newName(), { target: { value: 'Soir' } });
		await fireEvent.click(view.create());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
	});

	it('says so when the playlist could not be created', async () => {
		api.createPlaylist.mockRejectedValue(new Error('offline'));
		const view = await opened();

		await fireEvent.input(view.newName(), { target: { value: 'Soir' } });
		await fireEvent.click(view.create());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
		expect(api.addArticle).not.toHaveBeenCalled();
	});
});

describe('dismissing the panel', () => {
	// It floats over the article, so a press anywhere else has to close it: on a phone there is no
	// escape key and no obvious close button on a panel this small.
	it('closes when something outside it is pressed', async () => {
		const view = await opened();

		await fireEvent.pointerDown(document.body);

		await vi.waitFor(() => expect(view.panel()).toBeNull());
	});

	it('stays open when the press is inside it', async () => {
		const view = await opened();
		await vi.waitFor(() => expect(view.option('p1')).not.toBeNull());

		await fireEvent.pointerDown(view.option('p1')!);

		expect(view.panel()).not.toBeNull();
	});

	// A listener left on the document keeps firing on every press in the app, on a component that
	// is no longer there — the article page is left with the panel open on every navigation.
	it('stops listening once the page it is on is gone', async () => {
		const { container, unmount } = render(AddToPlaylist, { articleId: 'article-1' } as never);
		await fireEvent.click(container.querySelector('[data-test-add-to-playlist]')!);

		unmount();

		expect(() => fireEvent.pointerDown(document.body)).not.toThrow();
	});
});
