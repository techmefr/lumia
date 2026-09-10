import type { HttpClient } from '../../technical/http-client';
import type {
	AccessMode,
	AccessRequest,
	AccessRequestStatus,
	AccountUsage,
	InstanceSettings,
	InstanceSettingsUpdate
} from './types';

export function createInstanceApi(http: HttpClient) {
	/** The only instance setting a visitor may read, so the sign-in screen knows what to offer. */
	async function getAccessMode(): Promise<AccessMode> {
		const { access_mode } = await http.request<{ access_mode: AccessMode }>(
			'/instance/access-mode',
			{ auth: false }
		);
		return access_mode;
	}

	async function getSettings(): Promise<InstanceSettings> {
		return http.request<InstanceSettings>('/instance/settings');
	}

	async function updateSettings(payload: InstanceSettingsUpdate): Promise<InstanceSettings> {
		return http.request<InstanceSettings>('/instance/settings', {
			method: 'PATCH',
			body: payload
		});
	}

	async function listAccounts(): Promise<AccountUsage[]> {
		return http.request<AccountUsage[]>('/instance/accounts');
	}

	async function requestAccess(email: string, username: string): Promise<AccessRequest> {
		return http.request<AccessRequest>('/access-requests', {
			method: 'POST',
			body: { email, username },
			auth: false
		});
	}

	async function listAccessRequests(status?: AccessRequestStatus): Promise<AccessRequest[]> {
		const query = status ? `?request_status=${status}` : '';
		return http.request<AccessRequest[]>(`/access-requests${query}`);
	}

	async function approveAccessRequest(requestId: string): Promise<void> {
		await http.request(`/access-requests/${requestId}/approve`, { method: 'POST' });
	}

	async function rejectAccessRequest(requestId: string): Promise<void> {
		await http.request(`/access-requests/${requestId}/reject`, { method: 'POST' });
	}

	return {
		getAccessMode,
		getSettings,
		updateSettings,
		listAccounts,
		requestAccess,
		listAccessRequests,
		approveAccessRequest,
		rejectAccessRequest
	};
}

export type InstanceApi = ReturnType<typeof createInstanceApi>;
