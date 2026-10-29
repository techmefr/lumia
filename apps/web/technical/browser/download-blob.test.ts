import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { downloadBlob } from './download-blob';

beforeEach(() => {
	vi.useFakeTimers();
	URL.createObjectURL = vi.fn(() => 'blob:x');
	URL.revokeObjectURL = vi.fn();
	vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
});

afterEach(() => {
	vi.useRealTimers();
	vi.restoreAllMocks();
});

describe('downloadBlob', () => {
	it('clicks a temporary link and removes it afterwards', () => {
		downloadBlob(new Blob(['x']), 'book.epub');

		expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledOnce();
		expect(document.querySelector('a[download]')).toBeNull();
	});

	it('revokes the object url after the browser has had time to start the download', () => {
		downloadBlob(new Blob(['x']), 'book.epub');
		expect(URL.revokeObjectURL).not.toHaveBeenCalled();

		vi.advanceTimersByTime(10_000);

		expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:x');
	});
});
