import { beforeEach, describe, expect, it, vi } from 'vitest';

const plugin = vi.hoisted(() => ({
	checkPermissions: vi.fn(),
	requestPermissions: vi.fn(),
	schedule: vi.fn()
}));

vi.mock('@capacitor/local-notifications', () => ({ LocalNotifications: plugin }));

import {
	checkNativePermission,
	requestNativePermission,
	showNativeNotification
} from './native-notifier';

beforeEach(() => vi.clearAllMocks());

describe('native permission', () => {
	it.each([
		['granted', 'granted'],
		['denied', 'denied'],
		['prompt', 'default'],
		['prompt-with-rationale', 'default']
	])('maps the plugin answer %s to %s', async (display, expected) => {
		plugin.checkPermissions.mockResolvedValue({ display });
		expect(await checkNativePermission()).toBe(expected);
	});

	it('returns what the system answered when the reader is asked', async () => {
		plugin.requestPermissions.mockResolvedValue({ display: 'granted' });
		expect(await requestNativePermission()).toBe('granted');
	});
});

describe('showNativeNotification', () => {
	it('schedules one notification carrying the title and body', async () => {
		plugin.schedule.mockResolvedValue({ notifications: [] });
		await showNativeNotification('Lumia', '3 new articles');
		expect(plugin.schedule).toHaveBeenCalledWith({
			notifications: [{ id: expect.any(Number), title: 'Lumia', body: '3 new articles' }]
		});
	});

	it('reuses one id so a new alert replaces the previous one', async () => {
		plugin.schedule.mockResolvedValue({ notifications: [] });
		await showNativeNotification('Lumia', 'a');
		await showNativeNotification('Lumia', 'b');
		const ids = plugin.schedule.mock.calls.map((call) => call[0].notifications[0].id);
		expect(ids[0]).toBe(ids[1]);
	});
});
