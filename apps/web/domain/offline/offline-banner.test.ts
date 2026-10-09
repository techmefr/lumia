import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import OfflineBanner from './offline-banner.svelte';

describe('offline banner', () => {
	it('announces the offline state politely', () => {
		const { container } = render(OfflineBanner);
		const banner = container.querySelector('[data-test-offline-banner]');
		expect(banner?.getAttribute('role')).toBe('status');
		expect(banner?.textContent?.trim().length).toBeGreaterThan(0);
	});
});
