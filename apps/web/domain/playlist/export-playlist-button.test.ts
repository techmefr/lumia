import { ApiError, type ExportJob } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { setLocale } from '$technical/i18n/i18n.svelte';
import ExportPlaylistButton from './export-playlist-button.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		playlist: { exportPlaylistEpub: vi.fn(), getExport: vi.fn(), downloadExport: vi.fn() }
	}
}));

const api = vi.mocked(lumia.playlist);

type Props = Parameters<typeof ExportPlaylistButton>[1];

function job(status: ExportJob['status']): ExportJob {
	return { id: 'job-1', kind: 'playlist_epub', status, file_name: null };
}

function widget(props: Partial<Props> = {}) {
	const { container } = render(ExportPlaylistButton, {
		playlistId: 'list-1',
		name: 'Lectures du soir',
		pollMs: 0,
		...props
	} as Props);
	const button = () =>
		container.querySelector<HTMLButtonElement>('[data-test-export-playlist-button]')!;
	return { button, label: () => button().textContent?.trim().replace(/\s+/g, ' ') };
}

let download: { href: string; name: string } | null;

function toastMessages() {
	return toasts.toasts.map((item) => item.message);
}

beforeEach(() => {
	setLocale('fr');
	download = null;
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:book');
	vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
	vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
		this: HTMLAnchorElement
	) {
		download = { href: this.href, name: this.download };
	});
});

afterEach(() => vi.resetAllMocks());

describe('exporting a playlist as a book', () => {
	it('offers the export', () => {
		expect(widget().label()).toBe('Exporter en livre');
	});

	it('asks for its own playlist, waits for the worker, then hands the file to the browser', async () => {
		api.exportPlaylistEpub.mockResolvedValue(job('pending'));
		api.getExport
			.mockResolvedValueOnce(job('pending'))
			.mockResolvedValueOnce(job('pending'))
			.mockResolvedValueOnce(job('ready'));
		api.downloadExport.mockResolvedValue(new Blob(['epub']));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() => expect(download).not.toBeNull());
		expect(api.exportPlaylistEpub).toHaveBeenCalledWith('list-1');
		expect(api.getExport).toHaveBeenCalledTimes(3);
		expect(api.getExport).toHaveBeenCalledWith('job-1');
		expect(api.downloadExport).toHaveBeenCalledWith('job-1');
		expect(download?.name).toBe('Lectures du soir.epub');
		expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:book');
	});

	it('does not download anything before the job is ready', async () => {
		api.exportPlaylistEpub.mockResolvedValue(job('pending'));
		api.getExport.mockResolvedValue(job('pending'));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() => expect(api.getExport.mock.calls.length).toBeGreaterThan(2));
		expect(api.downloadExport).not.toHaveBeenCalled();
		expect(view.button().disabled).toBe(true);
		expect(view.label()).toBe('Fabrication du livre…');
	});

	it('reports a build that failed on the worker side', async () => {
		api.exportPlaylistEpub.mockResolvedValue(job('pending'));
		api.getExport.mockResolvedValue(job('failed'));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() =>
			expect(toastMessages()).toContain('Impossible de fabriquer le livre. Réessaie plus tard.')
		);
		expect(api.downloadExport).not.toHaveBeenCalled();
		expect(view.button().disabled).toBe(false);
	});

	it('gives up after the allowed number of looks', async () => {
		api.exportPlaylistEpub.mockResolvedValue(job('pending'));
		api.getExport.mockResolvedValue(job('pending'));
		const view = widget({ maxPolls: 3 });

		await fireEvent.click(view.button());

		await vi.waitFor(() =>
			expect(toastMessages()).toContain('Impossible de fabriquer le livre. Réessaie plus tard.')
		);
		expect(api.getExport).toHaveBeenCalledTimes(3);
	});

	it('tells the reader an empty playlist has nothing to export', async () => {
		api.exportPlaylistEpub.mockRejectedValue(new ApiError(422, { detail: 'empty_playlist' }));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() =>
			expect(toastMessages()).toContain('Cette playlist est vide, ajoute d’abord des articles.')
		);
		expect(api.getExport).not.toHaveBeenCalled();
	});

	it('tells the reader a playlist that is too large cannot be one book', async () => {
		api.exportPlaylistEpub.mockRejectedValue(new ApiError(413, { detail: 'playlist_too_large' }));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() =>
			expect(toastMessages()).toContain('Cette playlist est trop longue pour tenir dans un seul livre.')
		);
	});

	it('names the file after the playlist without the characters a file system refuses', async () => {
		api.exportPlaylistEpub.mockResolvedValue(job('pending'));
		api.getExport.mockResolvedValue(job('ready'));
		api.downloadExport.mockResolvedValue(new Blob(['epub']));
		const view = widget({ name: 'Q/A: "soir"' });

		await fireEvent.click(view.button());

		await vi.waitFor(() => expect(download).not.toBeNull());
		expect(download?.name).toBe('Q A soir.epub');
	});
});
