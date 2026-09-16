import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { articleSummary, playlistDetail, playlistSummary } from '../test-support/fixtures';
import PlaylistsPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		playlist: {
			listPlaylists: vi.fn(),
			createPlaylist: vi.fn(),
			renamePlaylist: vi.fn(),
			deletePlaylist: vi.fn(),
			createPlaylistForDuration: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia, { deep: true });

function playlistsPage() {
	const { container } = render(PlaylistsPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loading: () => q('[role="status"]'),
		error: () => q('[data-test-playlists-error]'),
		items: () => [...container.querySelectorAll('[data-test-playlist]')],
		item: (id: string) => q(`[data-test-playlist="${id}"]`),
		browse: () => q<HTMLAnchorElement>('a[href$="/articles"]'),
		newForm: () => q<HTMLFormElement>('[data-test-new-playlist-form]')!,
		newName: () => q<HTMLInputElement>('#new-playlist')!,
		fill: (minutes: number) => q<HTMLButtonElement>(`[data-test-fill-duration="${minutes}"]`)!,
		rename: (id: string) => q<HTMLButtonElement>(`[data-test-rename="${id}"]`)!,
		renameForm: () => q<HTMLFormElement>('[data-test-rename-form]'),
		renameInput: (id: string) => q<HTMLInputElement>(`#rename-${id}`)!,
		remove: (id: string) => q<HTMLButtonElement>(`[data-test-delete="${id}"]`)!
	};
}

async function withPlaylists(playlists = [playlistSummary('list-1')]) {
	api.playlist.listPlaylists.mockResolvedValue(playlists);
	const view = playlistsPage();
	await waitFor(() =>
		expect(playlists.length === 0 ? view.browse() !== null : view.items().length > 0).toBe(true)
	);
	return view;
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.playlist.listPlaylists.mockResolvedValue([]);
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('the playlist list', () => {
	it('shows one entry per playlist', async () => {
		const view = await withPlaylists([playlistSummary('list-1'), playlistSummary('list-2')]);

		expect(view.items()).toHaveLength(2);
	});

	it('points an empty collection at the article list', async () => {
		const view = await withPlaylists([]);

		expect(view.items()).toHaveLength(0);
		expect(view.browse()).not.toBeNull();
	});

	it('says so when the playlists cannot be fetched', async () => {
		api.playlist.listPlaylists.mockRejectedValue(new Error('offline'));
		const view = playlistsPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});
});

describe('creating a playlist', () => {
	it('creates it, clears the field and shows it in the list', async () => {
		const view = await withPlaylists([]);
		api.playlist.createPlaylist.mockResolvedValue(playlistSummary('list-9', { name: 'Trajet' }));
		api.playlist.listPlaylists.mockResolvedValue([playlistSummary('list-9', { name: 'Trajet' })]);

		await fireEvent.input(view.newName(), { target: { value: '  Trajet  ' } });
		await fireEvent.submit(view.newForm());

		await waitFor(() => expect(api.playlist.createPlaylist).toHaveBeenCalledWith('Trajet'));
		await waitFor(() => expect(view.item('list-9')).not.toBeNull());
		expect(view.newName().value).toBe('');
	});

	it('creates nothing from a name made only of spaces', async () => {
		const view = await withPlaylists([]);

		await fireEvent.input(view.newName(), { target: { value: '   ' } });
		await fireEvent.submit(view.newForm());

		expect(api.playlist.createPlaylist).not.toHaveBeenCalled();
	});
});

describe('filling a playlist by the time available', () => {
	it('asks for a playlist that fits the chosen duration and reloads the list', async () => {
		const view = await withPlaylists([]);
		api.playlist.createPlaylistForDuration.mockResolvedValue(
			playlistDetail('list-5', [articleSummary('a')])
		);

		await fireEvent.click(view.fill(25));

		await waitFor(() => expect(api.playlist.createPlaylistForDuration).toHaveBeenCalledWith(25));
		await waitFor(() => expect(api.playlist.listPlaylists).toHaveBeenCalledTimes(2));
	});

	// An empty result is not a failure, but it has to be said: the reader asked for 12 minutes and
	// nothing they follow is short enough.
	it('says nothing was short enough when the playlist comes back empty', async () => {
		const view = await withPlaylists([]);
		api.playlist.createPlaylistForDuration.mockResolvedValue(playlistDetail('list-5', []));

		await fireEvent.click(view.fill(12));

		await waitFor(() => expect(api.playlist.createPlaylistForDuration).toHaveBeenCalledWith(12));
		expect(view.error()).toBeNull();
	});

	it('re-enables the durations after a failure', async () => {
		const view = await withPlaylists([]);
		api.playlist.createPlaylistForDuration.mockRejectedValue(new Error('offline'));

		await fireEvent.click(view.fill(45));

		await waitFor(() => expect(view.fill(45).disabled).toBe(false));
	});
});

describe('renaming and deleting', () => {
	it('renames a playlist and closes the form', async () => {
		const view = await withPlaylists([playlistSummary('list-1')]);
		api.playlist.renamePlaylist.mockResolvedValue(playlistSummary('list-1', { name: 'Matin' }));

		await fireEvent.click(view.rename('list-1'));
		await waitFor(() => expect(view.renameForm()).not.toBeNull());
		await fireEvent.input(view.renameInput('list-1'), { target: { value: 'Matin' } });
		await fireEvent.submit(view.renameForm()!);

		await waitFor(() =>
			expect(api.playlist.renamePlaylist).toHaveBeenCalledWith('list-1', 'Matin')
		);
		await waitFor(() => expect(view.renameForm()).toBeNull());
	});

	it('renames nothing from an empty name', async () => {
		const view = await withPlaylists([playlistSummary('list-1')]);

		await fireEvent.click(view.rename('list-1'));
		await waitFor(() => expect(view.renameForm()).not.toBeNull());
		await fireEvent.input(view.renameInput('list-1'), { target: { value: '  ' } });
		await fireEvent.submit(view.renameForm()!);

		expect(api.playlist.renamePlaylist).not.toHaveBeenCalled();
	});

	it('deletes a playlist and drops it from the list', async () => {
		const view = await withPlaylists([playlistSummary('list-1')]);
		api.playlist.deletePlaylist.mockResolvedValue(undefined);
		api.playlist.listPlaylists.mockResolvedValue([]);

		await fireEvent.click(view.remove('list-1'));

		await waitFor(() => expect(api.playlist.deletePlaylist).toHaveBeenCalledWith('list-1'));
		await waitFor(() => expect(view.item('list-1')).toBeNull());
	});

	it('leaves the playlist in place when the deletion fails', async () => {
		const view = await withPlaylists([playlistSummary('list-1')]);
		api.playlist.deletePlaylist.mockRejectedValue(new Error('offline'));

		await fireEvent.click(view.remove('list-1'));

		await waitFor(() => expect(api.playlist.deletePlaylist).toHaveBeenCalled());
		expect(view.item('list-1')).not.toBeNull();
	});
});
