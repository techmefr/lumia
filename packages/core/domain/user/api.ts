import type { HttpClient } from '../../technical/http-client';
import type { TokenStore } from '../../technical/token-store';
import type { MagicLinkPurpose, Me, MeUpdate, TokenPair } from './types';

export interface OnboardAdminPayload {
	email: string;
	username: string;
	password: string;
	max_accounts?: number;
	disk_quota_mb?: number;
}

export function createUserApi(http: HttpClient, tokenStore: TokenStore) {
	function storeTokens(tokens: TokenPair): void {
		tokenStore.setTokens({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token });
	}

	async function onboardAdmin(payload: OnboardAdminPayload): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/onboarding/admin', { method: 'POST', body: payload, auth: false })
		);
	}

	async function login(email: string, password: string): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/auth/login', {
				method: 'POST',
				body: { email, password },
				auth: false
			})
		);
	}

	async function logout(): Promise<void> {
		const refreshToken = tokenStore.getRefreshToken();
		try {
			if (refreshToken) {
				await http.request('/auth/logout', {
					method: 'POST',
					body: { refresh_token: refreshToken }
				});
			}
		} finally {
			// Whatever the server answered, the session on this device goes. A logout that fails to
			// log out because the network was down leaves someone signed in on a shared machine,
			// which is the one outcome worse than an orphaned refresh token server-side.
			tokenStore.clear();
		}
	}

	async function requestMagicLink(
		email: string,
		purpose: MagicLinkPurpose = 'sign_in'
	): Promise<void> {
		await http.request('/auth/magic-link', {
			method: 'POST',
			body: { email, purpose },
			auth: false
		});
	}

	async function verifyMagicLink(token: string): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/auth/magic-link/verify', {
				method: 'POST',
				body: { token },
				auth: false
			})
		);
	}

	/**
	 * The change ends every session, so the pair it returns is what keeps this device signed in.
	 * `currentPassword` is null only for an account that has never had one — SSO or magic link.
	 */
	async function changePassword(
		currentPassword: string | null,
		newPassword: string
	): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/me/password', {
				method: 'POST',
				body: { current_password: currentPassword, new_password: newPassword }
			})
		);
	}

	async function resetPassword(token: string, newPassword: string): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/auth/password-reset', {
				method: 'POST',
				body: { token, new_password: newPassword },
				auth: false
			})
		);
	}

	async function getMe(): Promise<Me> {
		return http.request<Me>('/me');
	}

	async function updateMe(payload: MeUpdate): Promise<Me> {
		return http.request<Me>('/me', { method: 'PATCH', body: payload });
	}

	function isAuthenticated(): boolean {
		return tokenStore.getAccessToken() !== null;
	}

	return {
		onboardAdmin,
		login,
		logout,
		requestMagicLink,
		verifyMagicLink,
		changePassword,
		resetPassword,
		getMe,
		updateMe,
		isAuthenticated
	};
}

export type UserApi = ReturnType<typeof createUserApi>;
