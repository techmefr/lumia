import type { Role } from '../user/types';

/** How a new account can come to exist on the instance. */
export type AccessMode = 'closed' | 'on_approval' | 'open';

export type AccessRequestStatus = 'pending' | 'approved' | 'rejected';

export interface InstanceSettings {
	max_accounts: number;
	/** The cap on what a single account may store, not on the whole instance. */
	disk_quota_mb: number;
	access_mode: AccessMode;
	account_count: number;
}

export interface InstanceSettingsUpdate {
	max_accounts?: number;
	disk_quota_mb?: number;
	access_mode?: AccessMode;
}

export interface AccountUsage {
	id: string;
	email: string;
	username: string;
	role: Role;
	used_mb: number;
	quota_mb: number;
}

export interface AccessRequest {
	id: string;
	email: string;
	username: string;
	status: AccessRequestStatus;
	created_at: string;
	decided_at: string | null;
}
