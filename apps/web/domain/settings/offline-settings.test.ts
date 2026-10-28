import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { getOfflineLimit } from '$technical/offline/offline-limit';
import { runOfflineSync } from '$technical/offline/offline-runner';
import OfflineSettings from './offline-settings.svelte';

vi.mock('$technical/offline/offline-runner', () => ({ runOfflineSync: vi.fn() }));

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

function limitSelect(container: HTMLElement) {
	return container.querySelector<HTMLSelectElement>('[data-test-offline-limit]')!;
}

describe('the offline settings', () => {
	it('offers a disabled option and several caps, on the stored one', () => {
		localStorage.setItem('lumia-offline-limit', '100');

		const { container } = render(OfflineSettings);

		const select = limitSelect(container);
		expect(select.value).toBe('100');
		expect([...select.options].map((option) => option.value)).toEqual([
			'0',
			'25',
			'50',
			'100',
			'200'
		]);
	});

	it('stores a new cap and starts a download pass at once', async () => {
		const { container } = render(OfflineSettings);

		await fireEvent.change(limitSelect(container), { target: { value: '25' } });

		expect(getOfflineLimit()).toBe(25);
		expect(runOfflineSync).toHaveBeenCalledWith(true);
	});
});
