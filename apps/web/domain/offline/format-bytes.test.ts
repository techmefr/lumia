import { describe, expect, it } from 'vitest';
import { formatBytes } from './format-bytes';

describe('formatBytes', () => {
	it('shows zero plainly', () => {
		expect(formatBytes(0)).toBe('0 B');
	});

	it('keeps small counts in bytes, with no decimal', () => {
		expect(formatBytes(512)).toBe('512 B');
	});

	it('switches to kilobytes past 1024 bytes', () => {
		expect(formatBytes(2048)).toBe('2.0 KB');
	});

	it('switches to megabytes past 1024 kilobytes', () => {
		expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB');
	});
});
