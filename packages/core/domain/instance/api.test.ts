import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createInstanceApi } from './api';

function api(replies: unknown[] = [{}]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, instance: createInstanceApi(recorder.http) };
}

describe('the instance settings', () => {
	it('reads the access mode without a session', async () => {
		const { instance, last } = api([{ access_mode: 'on_approval' }]);
		await expect(instance.getAccessMode()).resolves.toBe('on_approval');
		expect(last()).toMatchObject({ path: '/instance/access-mode', method: 'GET', auth: false });
	});

	it('reads the quotas as the admin', async () => {
		const settings = {
			max_accounts: 10,
			disk_quota_mb: 1000,
			access_mode: 'closed',
			account_count: 2
		};
		const { instance, last } = api([settings]);
		await expect(instance.getSettings()).resolves.toEqual(settings);
		expect(last()).toMatchObject({ path: '/instance/settings', method: 'GET', auth: true });
	});

	it('sends only the quotas that changed', async () => {
		const { instance, last } = api([{}]);
		await instance.updateSettings({ disk_quota_mb: 2000 });
		expect(last()).toMatchObject({
			path: '/instance/settings',
			method: 'PATCH',
			body: { disk_quota_mb: 2000 }
		});
	});

	it('lists the accounts with what each one stores', async () => {
		const { instance, last } = api([[{ id: 'user-1', used_mb: 12 }]]);
		await expect(instance.listAccounts()).resolves.toEqual([{ id: 'user-1', used_mb: 12 }]);
		expect(last()).toMatchObject({ path: '/instance/accounts', method: 'GET' });
	});
});

describe('the access requests', () => {
	it('lets a visitor ask for an account without a session', async () => {
		const { instance, last } = api([{ id: 'request-1' }]);
		await instance.requestAccess('visiteur@example.test', 'visiteur');
		expect(last()).toMatchObject({
			path: '/access-requests',
			method: 'POST',
			body: { email: 'visiteur@example.test', username: 'visiteur' },
			auth: false
		});
	});

	it('lists every request when no status is asked for', async () => {
		const { instance, last } = api([[]]);
		await instance.listAccessRequests();
		expect(last()).toMatchObject({ path: '/access-requests', method: 'GET' });
	});

	it('filters the list on a status', async () => {
		const { instance, last } = api([[]]);
		await instance.listAccessRequests('pending');
		expect(last()).toMatchObject({ path: '/access-requests?request_status=pending' });
	});

	it('approves one', async () => {
		const { instance, last } = api([undefined]);
		await instance.approveAccessRequest('request-1');
		expect(last()).toMatchObject({
			path: '/access-requests/request-1/approve',
			method: 'POST'
		});
	});

	it('rejects one', async () => {
		const { instance, last } = api([undefined]);
		await instance.rejectAccessRequest('request-1');
		expect(last()).toMatchObject({ path: '/access-requests/request-1/reject', method: 'POST' });
	});
});
