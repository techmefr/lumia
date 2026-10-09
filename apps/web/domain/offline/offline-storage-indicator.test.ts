import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import OfflineStorageIndicator from './offline-storage-indicator.svelte';

function indicator(props: { bytesUsed: number; capBytes: number; articleCount: number }) {
	const { container } = render(OfflineStorageIndicator, props);
	return {
		bar: () => container.querySelector<HTMLElement>('[data-test-offline-storage-bar]'),
		text: () => container.querySelector('[data-test-offline-storage]')?.textContent ?? ''
	};
}

describe('offline storage indicator', () => {
	it('shows how much is used against the cap', () => {
		const text = indicator({ bytesUsed: 1024, capBytes: 2048, articleCount: 3 }).text();
		expect(text).toContain('1.0 KB');
		expect(text).toContain('2.0 KB');
		expect(text).toContain('3');
	});

	it('fills half the bar at half the cap', () => {
		const bar = indicator({ bytesUsed: 1024, capBytes: 2048, articleCount: 1 }).bar();
		expect(bar?.getAttribute('style')).toContain('width: 50%');
	});

	it('never overflows the bar past the cap', () => {
		const bar = indicator({ bytesUsed: 4096, capBytes: 2048, articleCount: 5 }).bar();
		expect(bar?.getAttribute('style')).toContain('width: 100%');
	});
});
