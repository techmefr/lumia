import { ApiError, type AlertNotification, type SavedSearch } from '@lumia/core';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import AlertsPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		savedSearch: {
			listSavedSearches: vi.fn(),
			createSavedSearch: vi.fn(),
			updateSavedSearch: vi.fn(),
			deleteSavedSearch: vi.fn(),
			listNotifications: vi.fn(),
			markNotificationsRead: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia, { deep: true }).savedSearch;

function search(overrides: Partial<SavedSearch> = {}): SavedSearch {
	return {
		id: 's1',
		name: 'Rust',
		query: 'rust',
		feed_id: null,
		folder_id: null,
		alert: true,
		unread_count: 4,
		...overrides
	};
}

function notification(overrides: Partial<AlertNotification> = {}): AlertNotification {
	return {
		id: 'n1',
		saved_search_id: 's1',
		saved_search_name: 'Rust',
		article_id: 'a1',
		article_title: 'Rust ships',
		read: false,
		created_at: '2026-10-21T10:00:00Z',
		...overrides
	};
}

function page() {
	const { container } = render(AlertsPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		searches: () => [...container.querySelectorAll('[data-test-search]')],
		link: () => q<HTMLAnchorElement>('[data-test-search-link]'),
		unread: () => q('[data-test-search-unread]')?.textContent?.trim(),
		empty: () => q('[data-test-searches-empty]'),
		error: () => q('[data-test-alerts-error]')?.textContent?.trim(),
		name: () => q<HTMLInputElement>('input[data-test-search-name]')!,
		query: () => q<HTMLInputElement>('input[data-test-search-query]')!,
		alertBox: () => q<HTMLInputElement>('[data-test-search-alert]')!,
		submit: () => q<HTMLButtonElement>('[data-test-search-submit]')!,
		toggle: () => q<HTMLInputElement>('[data-test-search-toggle]')!,
		remove: () => q<HTMLButtonElement>('[data-test-search-remove]')!,
		notifications: () => [...container.querySelectorAll('[data-test-notification]')],
		notificationsEmpty: () => q('[data-test-notifications-empty]'),
		markAll: () => q<HTMLButtonElement>('[data-test-mark-all-read]')
	};
}

async function loaded(searches: SavedSearch[] = [search()], items: AlertNotification[] = []) {
	api.listSavedSearches.mockResolvedValue(searches);
	api.listNotifications.mockResolvedValue({
		unread_count: items.filter((item) => !item.read).length,
		items
	});
	const view = page();
	await waitFor(() =>
		expect(searches.length === 0 ? view.empty() : view.searches().length).toBeTruthy()
	);
	return view;
}

beforeEach(() => {
	vi.mocked(lumia.user.isAuthenticated).mockReturnValue(true);
	api.listSavedSearches.mockResolvedValue([]);
	api.listNotifications.mockResolvedValue({ unread_count: 0, items: [] });
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('the saved searches', () => {
	it('lists each with its unread count and a link that replays the search', async () => {
		const view = await loaded([search({ feed_id: 'f1' })]);

		expect(view.unread()).toContain('4');
		const href = view.link()?.getAttribute('href') ?? '';
		expect(href).toContain('q=rust');
		expect(href).toContain('feed_id=f1');
	});

	it('carries the folder scope in the link', async () => {
		const view = await loaded([search({ folder_id: 'd1' })]);

		expect(view.link()?.getAttribute('href')).toContain('folder_id=d1');
	});

	it('says so when there are none', async () => {
		const view = await loaded([]);

		expect(view.empty()).not.toBeNull();
	});

	it('shows an error when the lists cannot be loaded', async () => {
		api.listSavedSearches.mockRejectedValue(new Error('down'));
		const view = page();

		await waitFor(() => expect(view.error()).toBeTruthy());
	});
});

describe('creating a search', () => {
	it('sends the trimmed query as an alert by default and reloads', async () => {
		api.createSavedSearch.mockResolvedValue(search());
		const view = await loaded([]);

		await fireEvent.input(view.query(), { target: { value: '  rust  ' } });
		await fireEvent.click(view.submit());

		await waitFor(() =>
			expect(api.createSavedSearch).toHaveBeenCalledWith({
				name: 'rust',
				query: 'rust',
				alert: true
			})
		);
		await waitFor(() => expect(api.listSavedSearches).toHaveBeenCalledTimes(2));
	});

	it('uses the given name and the unticked alert flag', async () => {
		api.createSavedSearch.mockResolvedValue(search());
		const view = await loaded([]);

		await fireEvent.input(view.name(), { target: { value: 'Veille' } });
		await fireEvent.input(view.query(), { target: { value: 'rust' } });
		await fireEvent.click(view.alertBox());
		await fireEvent.click(view.submit());

		await waitFor(() =>
			expect(api.createSavedSearch).toHaveBeenCalledWith({
				name: 'Veille',
				query: 'rust',
				alert: false
			})
		);
	});

	it('refuses a one-character query without calling the api', async () => {
		const view = await loaded([]);

		await fireEvent.input(view.query(), { target: { value: 'a' } });
		await fireEvent.click(view.submit());

		expect(view.error()).toBeTruthy();
		expect(api.createSavedSearch).not.toHaveBeenCalled();
	});

	it('explains a name already taken', async () => {
		api.createSavedSearch.mockRejectedValue(new ApiError(409, null));
		const view = await loaded([]);
		await fireEvent.input(view.query(), { target: { value: 'rust' } });

		await fireEvent.click(view.submit());

		await waitFor(() => expect(view.error()).toBeTruthy());
		expect(view.error()).not.toBe('');
	});

	it('reports any other failure', async () => {
		api.createSavedSearch.mockRejectedValue(new Error('down'));
		const view = await loaded([]);
		await fireEvent.input(view.query(), { target: { value: 'rust' } });

		await fireEvent.click(view.submit());

		await waitFor(() => expect(view.error()).toBeTruthy());
	});
});

describe('managing a search', () => {
	it('turns the alert off', async () => {
		api.updateSavedSearch.mockResolvedValue(search({ alert: false }));
		const view = await loaded();

		await fireEvent.click(view.toggle());

		await waitFor(() =>
			expect(api.updateSavedSearch).toHaveBeenCalledWith('s1', { alert: false })
		);
	});

	it('survives a failed toggle', async () => {
		api.updateSavedSearch.mockRejectedValue(new Error('down'));
		const view = await loaded();

		await fireEvent.click(view.toggle());

		await waitFor(() => expect(api.updateSavedSearch).toHaveBeenCalled());
		expect(view.searches()).toHaveLength(1);
	});

	it('deletes it', async () => {
		api.deleteSavedSearch.mockResolvedValue(undefined);
		const view = await loaded();

		await fireEvent.click(view.remove());

		await waitFor(() => expect(api.deleteSavedSearch).toHaveBeenCalledWith('s1'));
	});

	it('survives a failed delete', async () => {
		api.deleteSavedSearch.mockRejectedValue(new Error('down'));
		const view = await loaded();

		await fireEvent.click(view.remove());

		await waitFor(() => expect(api.deleteSavedSearch).toHaveBeenCalled());
		expect(view.searches()).toHaveLength(1);
	});
});

describe('the notifications', () => {
	it('lists them, unread ones marked, each linking to its article', async () => {
		const view = await loaded(
			[search()],
			[notification(), notification({ id: 'n2', article_id: 'a2', read: true })]
		);

		expect(view.notifications()).toHaveLength(2);
		expect(view.notifications()[0].getAttribute('data-test-notification-read')).toBe('false');
		expect(view.notifications()[1].getAttribute('data-test-notification-read')).toBe('true');
		expect(view.notifications()[0].querySelector('a')?.getAttribute('href')).toContain(
			'/articles/a1'
		);
	});

	it('says so when there are none', async () => {
		const view = await loaded();

		expect(view.notificationsEmpty()).not.toBeNull();
		expect(view.markAll()).toBeNull();
	});

	it('marks everything read', async () => {
		api.markNotificationsRead.mockResolvedValue(undefined);
		const view = await loaded([search()], [notification()]);

		await fireEvent.click(view.markAll() as HTMLButtonElement);

		await waitFor(() => expect(api.markNotificationsRead).toHaveBeenCalledWith());
	});

	it('survives a failed mark', async () => {
		api.markNotificationsRead.mockRejectedValue(new Error('down'));
		const view = await loaded([search()], [notification()]);

		await fireEvent.click(view.markAll() as HTMLButtonElement);

		await waitFor(() => expect(api.markNotificationsRead).toHaveBeenCalled());
		expect(view.notifications()).toHaveLength(1);
	});
});
