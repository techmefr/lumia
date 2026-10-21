import { ApiError } from '@lumia/core';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import ReadingListImport from './reading-list-import.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { article: { importReadingList: vi.fn(), getReadingListImportProgress: vi.fn() } }
}));

const api = vi.mocked(lumia.article);

function view() {
	const { container } = render(ReadingListImport);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		source: () => q<HTMLSelectElement>('[data-test-reading-import-source]')!,
		input: () => q<HTMLInputElement>('[data-test-reading-import-input]')!,
		progress: () => q('[data-test-reading-import-progress]'),
		error: () => q('[data-test-reading-import-error]')
	};
}

function exportFile() {
	return new File(['x'], 'export.csv');
}

beforeEach(() => {
	api.importReadingList.mockReset();
	api.getReadingListImportProgress.mockReset();
});

afterEach(() => {
	cleanup();
	vi.useRealTimers();
});

describe('importing a reading list', () => {
	it('sends the file with the chosen source and reports the finished counts', async () => {
		api.importReadingList.mockResolvedValue({ import_id: 'imp', total: 3 });
		api.getReadingListImportProgress.mockResolvedValue({
			total: 3,
			saved: 2,
			failed: 1,
			finished: true
		});
		const page = view();
		const file = exportFile();

		await fireEvent.change(page.source(), { target: { value: 'instapaper' } });
		await fireEvent.change(page.input(), { target: { files: [file] } });

		await waitFor(() => expect(page.progress()?.textContent).toContain('2'));
		expect(api.importReadingList).toHaveBeenCalledWith('instapaper', file);
		expect(api.getReadingListImportProgress).toHaveBeenCalledWith('imp');
		expect(page.error()).toBeNull();
	});

	it('keeps polling until the worker has finished', async () => {
		vi.useFakeTimers();
		api.importReadingList.mockResolvedValue({ import_id: 'imp', total: 2 });
		api.getReadingListImportProgress
			.mockResolvedValueOnce({ total: 2, saved: 1, failed: 0, finished: false })
			.mockResolvedValueOnce({ total: 2, saved: 2, failed: 0, finished: true });
		const page = view();

		await fireEvent.change(page.input(), { target: { files: [exportFile()] } });
		await vi.advanceTimersByTimeAsync(2500);

		expect(api.getReadingListImportProgress).toHaveBeenCalledTimes(2);
		expect(page.progress()).not.toBeNull();
	});

	it('does not poll an export with nothing in it', async () => {
		api.importReadingList.mockResolvedValue({ import_id: 'imp', total: 0 });
		const page = view();

		await fireEvent.change(page.input(), { target: { files: [exportFile()] } });

		await waitFor(() => expect(page.progress()).not.toBeNull());
		expect(api.getReadingListImportProgress).not.toHaveBeenCalled();
	});

	it('reports an export the backend refused', async () => {
		api.importReadingList.mockRejectedValue(new ApiError(400, {}));
		const page = view();

		await fireEvent.change(page.input(), { target: { files: [exportFile()] } });

		await waitFor(() => expect(page.error()).not.toBeNull());
	});

	it('says an export is too large rather than that it is malformed', async () => {
		api.importReadingList.mockRejectedValue(new ApiError(413, {}));
		const page = view();

		await fireEvent.change(page.input(), { target: { files: [exportFile()] } });

		await waitFor(() => expect(page.error()?.textContent).toContain('too large'));
	});

	it('reports a progress lookup that fails', async () => {
		api.importReadingList.mockResolvedValue({ import_id: 'imp', total: 1 });
		api.getReadingListImportProgress.mockRejectedValue(new Error('down'));
		const page = view();

		await fireEvent.change(page.input(), { target: { files: [exportFile()] } });

		await waitFor(() => expect(page.error()).not.toBeNull());
	});

	it('ignores a change that carries no file', async () => {
		const page = view();

		await fireEvent.change(page.input(), { target: { files: [] } });

		expect(api.importReadingList).not.toHaveBeenCalled();
	});
});
