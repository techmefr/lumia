import { cleanup, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import AlertBell from './alert-bell.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { savedSearch: { listNotifications: vi.fn() } }
}));

const api = vi.mocked(lumia.savedSearch);

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

function bell() {
	const { container } = render(AlertBell);
	return {
		link: () => container.querySelector('[data-test-alert-bell]'),
		badge: () => container.querySelector('[data-test-alert-badge]')
	};
}

describe('the alert bell', () => {
	it('shows the unread count in a badge and in its accessible name', async () => {
		api.listNotifications.mockResolvedValue({ unread_count: 3, items: [] });
		const view = bell();

		await waitFor(() => expect(view.badge()?.textContent?.trim()).toBe('3'));
		expect(view.link()?.getAttribute('aria-label')).toContain('3');
	});

	it('caps a long count', async () => {
		api.listNotifications.mockResolvedValue({ unread_count: 250, items: [] });
		const view = bell();

		await waitFor(() => expect(view.badge()?.textContent?.trim()).toBe('99+'));
	});

	it('shows no badge when nothing is unread', async () => {
		api.listNotifications.mockResolvedValue({ unread_count: 0, items: [] });
		const view = bell();

		await waitFor(() => expect(api.listNotifications).toHaveBeenCalled());
		expect(view.badge()).toBeNull();
	});

	it('stays quiet when the api is unreachable', async () => {
		api.listNotifications.mockRejectedValue(new Error('offline'));
		const view = bell();

		await waitFor(() => expect(api.listNotifications).toHaveBeenCalled());
		expect(view.badge()).toBeNull();
		expect(view.link()).not.toBeNull();
	});
});
