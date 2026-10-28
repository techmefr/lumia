import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const notifier = vi.hoisted(() => ({
	checkNativePermission: vi.fn(),
	requestNativePermission: vi.fn(),
	showNativeNotification: vi.fn()
}));

vi.mock('./native-notifier', () => notifier);
vi.mock('$technical/platform/native-platform', () => ({ isNativePlatform: () => true }));

beforeEach(() => {
	localStorage.clear();
	vi.resetModules();
	vi.clearAllMocks();
	vi.stubGlobal('Notification', undefined);
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.useRealTimers();
});

describe('on a native platform', () => {
	it('is never reported as unsupported although the web Notification api is missing', async () => {
		const store = await import('./notification-store.svelte');
		expect(store.permissionState()).toBe('default');
	});

	it('reads the permission from the system when refreshed', async () => {
		notifier.checkNativePermission.mockResolvedValue('granted');
		const store = await import('./notification-store.svelte');
		expect(await store.refreshPermission()).toBe('granted');
		expect(store.permissionState()).toBe('granted');
	});

	it('asks the system for permission and remembers the answer', async () => {
		notifier.requestNativePermission.mockResolvedValue('denied');
		const store = await import('./notification-store.svelte');
		expect(await store.requestPermission()).toBe('denied');
		expect(store.permissionState()).toBe('denied');
	});

	it('raises the alert through the native notifier when the app is in the background', async () => {
		vi.useFakeTimers();
		Object.defineProperty(document, 'visibilityState', {
			configurable: true,
			get: () => 'hidden'
		});
		notifier.checkNativePermission.mockResolvedValue('granted');
		notifier.showNativeNotification.mockResolvedValue(undefined);
		const store = await import('./notification-store.svelte');
		await store.refreshPermission();
		store.updateNotificationSettings({
			enabled: true,
			intervalMinutes: 15,
			threshold: 1,
			quietFromHour: 0,
			quietToHour: 0
		});
		let total = 5;
		const stop = store.watchUnread(async () => total);
		await vi.advanceTimersByTimeAsync(0);
		total = 9;
		await vi.advanceTimersByTimeAsync(15 * 60_000);
		stop();
		expect(notifier.showNativeNotification).toHaveBeenCalledWith('Lumia', expect.any(String));
	});
});
