import { afterEach, describe, expect, it, vi } from 'vitest';
import { copyToClipboard } from './copy-to-clipboard';

afterEach(() => vi.unstubAllGlobals());

describe('copyToClipboard', () => {
	it('writes the text and reports success', async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		vi.stubGlobal('navigator', { clipboard: { writeText } });

		await expect(copyToClipboard('abc')).resolves.toBe(true);
		expect(writeText).toHaveBeenCalledWith('abc');
	});

	it('reports failure instead of throwing when the browser refuses', async () => {
		vi.stubGlobal('navigator', {
			clipboard: { writeText: vi.fn().mockRejectedValue(new Error('denied')) }
		});

		await expect(copyToClipboard('abc')).resolves.toBe(false);
	});

	it('reports failure when the clipboard api is missing', async () => {
		vi.stubGlobal('navigator', {});

		await expect(copyToClipboard('abc')).resolves.toBe(false);
	});
});
