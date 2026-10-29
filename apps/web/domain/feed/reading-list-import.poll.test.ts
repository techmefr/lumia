import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import ReadingListImport from './reading-list-import.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { article: { importReadingList: vi.fn(), getReadingListImportProgress: vi.fn() } }
}));

const api = vi.mocked(lumia.article);

beforeEach(() => vi.useFakeTimers());

afterEach(() => {
	cleanup();
	vi.useRealTimers();
	vi.clearAllMocks();
});

describe('polling the import progress', () => {
	it('stops polling once the component is gone, even when a request was in flight', async () => {
		api.importReadingList.mockResolvedValue({ import_id: 'i1', total: 5 } as never);
		let release: (value: never) => void = () => {};
		api.getReadingListImportProgress.mockImplementation(
			() => new Promise((resolve) => (release = resolve as typeof release))
		);
		const { container, unmount } = render(ReadingListImport);
		const input = container.querySelector<HTMLInputElement>('input[type="file"]')!;
		Object.defineProperty(input, 'files', { value: [new File(['x'], 'a.html')] });

		await fireEvent.change(input);
		await vi.advanceTimersByTimeAsync(0);
		unmount();
		release({ total: 5, saved: 1, failed: 0, finished: false } as never);
		await vi.advanceTimersByTimeAsync(10000);

		expect(api.getReadingListImportProgress).toHaveBeenCalledTimes(1);
	});
});
