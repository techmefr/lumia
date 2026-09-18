import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { isOnline, watchConnectivity } from './connectivity.svelte';

describe('connectivity', () => {
	let stop: (() => void) | null = null;

	// The module holds one shared `online` flag, like the app's own singleton does — reset it
	// before every test rather than assuming the previous test left it the way it started.
	beforeEach(() => {
		const reset = watchConnectivity();
		window.dispatchEvent(new Event('online'));
		reset();
	});

	afterEach(() => {
		stop?.();
		stop = null;
	});

	it('reflects the browser going offline', () => {
		stop = watchConnectivity();
		window.dispatchEvent(new Event('offline'));
		expect(isOnline()).toBe(false);
	});

	it('reflects the browser coming back online', () => {
		stop = watchConnectivity();
		window.dispatchEvent(new Event('offline'));
		window.dispatchEvent(new Event('online'));
		expect(isOnline()).toBe(true);
	});

	it('stops listening once torn down', () => {
		stop = watchConnectivity();
		stop();
		stop = null;
		window.dispatchEvent(new Event('offline'));
		expect(isOnline()).toBe(true);
	});
});
