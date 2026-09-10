import type { AccessRequest, AccountUsage, InstanceSettings } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import InstanceAdmin from './instance-admin.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		instance: {
			getSettings: vi.fn(),
			updateSettings: vi.fn(),
			listAccounts: vi.fn(),
			listAccessRequests: vi.fn(),
			approveAccessRequest: vi.fn(),
			rejectAccessRequest: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.instance);

const SETTINGS: InstanceSettings = {
	max_accounts: 10,
	disk_quota_mb: 1000,
	access_mode: 'closed',
	account_count: 2
};

const ACCOUNTS: AccountUsage[] = [
	{
		id: 'user-1',
		email: 'admin@example.test',
		username: 'admin',
		role: 'admin',
		used_mb: 12,
		quota_mb: 1000
	},
	{
		id: 'user-2',
		email: 'membre@example.test',
		username: 'membre',
		role: 'member',
		used_mb: 3,
		quota_mb: 1000
	}
];

const PENDING: AccessRequest = {
	id: 'request-1',
	email: 'visiteur@example.test',
	username: 'visiteur',
	status: 'pending',
	created_at: '2026-09-01T09:00:00Z',
	decided_at: null
};

function panel() {
	const { container } = render(InstanceAdmin);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loading: () => q('[data-test-admin-loading]'),
		unavailable: () => q('[data-test-admin-unavailable]'),
		body: () => q('[data-test-admin-panel]'),
		error: () => q('[data-test-admin-error]'),
		maxAccounts: () => q<HTMLInputElement>('[data-test-max-accounts]')!,
		quota: () => q<HTMLInputElement>('[data-test-account-quota]')!,
		accessMode: () => q<HTMLSelectElement>('[data-test-access-mode]')!,
		save: () => q<HTMLButtonElement>('[data-test-admin-save]')!,
		accountRows: () => container.querySelectorAll('[data-test-account-row]'),
		requests: () => container.querySelectorAll('[data-test-access-request]'),
		noRequests: () => q('[data-test-no-requests]'),
		approve: () => q<HTMLButtonElement>('[data-test-approve-request]')!,
		reject: () => q<HTMLButtonElement>('[data-test-reject-request]')!
	};
}

beforeEach(() => {
	vi.clearAllMocks();
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	api.getSettings.mockResolvedValue({ ...SETTINGS });
	api.listAccounts.mockResolvedValue([...ACCOUNTS]);
	api.listAccessRequests.mockResolvedValue([{ ...PENDING }]);
	api.updateSettings.mockResolvedValue({ ...SETTINGS });
	api.approveAccessRequest.mockResolvedValue(undefined);
	api.rejectAccessRequest.mockResolvedValue(undefined);
});

describe('the quotas', () => {
	it('shows what the instance currently allows', async () => {
		const view = panel();
		expect(view.loading()).not.toBeNull();

		await waitFor(() => expect(view.body()).not.toBeNull());
		expect(view.maxAccounts().value).toBe('10');
		expect(view.quota().value).toBe('1000');
		expect(view.accessMode().value).toBe('closed');
	});

	it('sends the three settings together and confirms', async () => {
		const view = panel();
		await waitFor(() => expect(view.body()).not.toBeNull());

		await fireEvent.input(view.maxAccounts(), { target: { value: '25' } });
		await fireEvent.input(view.quota(), { target: { value: '2500' } });
		await fireEvent.change(view.accessMode(), { target: { value: 'on_approval' } });
		await fireEvent.click(view.save());

		await waitFor(() =>
			expect(api.updateSettings).toHaveBeenCalledWith({
				max_accounts: 25,
				disk_quota_mb: 2500,
				access_mode: 'on_approval'
			})
		);
		await waitFor(() => expect(toasts.toasts).toHaveLength(1));
	});

	it('says so when the save is refused', async () => {
		api.updateSettings.mockRejectedValue(new Error('refused'));
		const view = panel();
		await waitFor(() => expect(view.body()).not.toBeNull());

		await fireEvent.click(view.save());

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('shows nothing but an unavailable notice when the api refuses the read', async () => {
		api.getSettings.mockRejectedValue(new Error('forbidden'));
		const view = panel();

		await waitFor(() => expect(view.unavailable()).not.toBeNull());
		expect(view.body()).toBeNull();
		expect(view.accountRows().length).toBe(0);
	});
});

describe('the accounts', () => {
	it('lists each one with what it stores', async () => {
		const view = panel();
		await waitFor(() => expect(view.body()).not.toBeNull());

		expect(view.accountRows().length).toBe(2);
		expect(view.accountRows()[1].textContent).toContain('membre@example.test');
		expect(view.accountRows()[1].textContent).toContain('3 / 1000');
	});
});

describe('the access requests', () => {
	it('only asks for the pending ones', async () => {
		const view = panel();
		await waitFor(() => expect(view.body()).not.toBeNull());

		expect(api.listAccessRequests).toHaveBeenCalledWith('pending');
		expect(view.requests().length).toBe(1);
	});

	it('approves one and reloads the panel', async () => {
		const view = panel();
		await waitFor(() => expect(view.body()).not.toBeNull());
		api.listAccessRequests.mockResolvedValue([]);

		await fireEvent.click(view.approve());

		await waitFor(() => expect(api.approveAccessRequest).toHaveBeenCalledWith('request-1'));
		await waitFor(() => expect(view.noRequests()).not.toBeNull());
	});

	it('rejects one', async () => {
		const view = panel();
		await waitFor(() => expect(view.body()).not.toBeNull());
		api.listAccessRequests.mockResolvedValue([]);

		await fireEvent.click(view.reject());

		await waitFor(() => expect(api.rejectAccessRequest).toHaveBeenCalledWith('request-1'));
		await waitFor(() => expect(view.requests().length).toBe(0));
	});

	it('says so when a decision fails', async () => {
		api.approveAccessRequest.mockRejectedValue(new Error('conflict'));
		const view = panel();
		await waitFor(() => expect(view.body()).not.toBeNull());

		await fireEvent.click(view.approve());

		await waitFor(() => expect(view.error()).not.toBeNull());
	});
});
