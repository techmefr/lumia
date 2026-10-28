import { afterEach, describe, expect, it, vi } from 'vitest';
import { connectivity, watchConnectivity } from './connectivity.svelte';

afterEach(() => {
	vi.restoreAllMocks();
	connectivity.online = true;
});

describe('watchConnectivity', () => {
	it('follows the browser going offline and back, and tells the caller about the return', () => {
		const onReconnect = vi.fn();
		const stop = watchConnectivity(onReconnect);

		window.dispatchEvent(new Event('offline'));
		expect(connectivity.online).toBe(false);
		expect(onReconnect).not.toHaveBeenCalled();

		window.dispatchEvent(new Event('online'));
		expect(connectivity.online).toBe(true);
		expect(onReconnect).toHaveBeenCalledTimes(1);
		stop();
	});

	it('starts from what the browser reports', () => {
		vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false);

		const stop = watchConnectivity(() => {});

		expect(connectivity.online).toBe(false);
		stop();
	});

	it('stops listening when torn down', () => {
		const onReconnect = vi.fn();
		const stop = watchConnectivity(onReconnect);
		stop();

		window.dispatchEvent(new Event('online'));

		expect(onReconnect).not.toHaveBeenCalled();
	});
});
