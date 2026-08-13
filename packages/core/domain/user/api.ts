import type { HttpClient } from '../../technical/http-client';
import type { TokenStore } from '../../technical/token-store';
import type { Me, MeUpdate, TokenPair } from './types';

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
		if (refreshToken) {
			await http.request('/auth/logout', { method: 'POST', body: { refresh_token: refreshToken } });
		}
		tokenStore.clear();
	}

	async function requestMagicLink(email: string): Promise<void> {
		await http.request('/auth/magic-link', { method: 'POST', body: { email }, auth: false });
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

	async function getMe(): Promise<Me> {
		return http.request<Me>('/me');
	}

	async function updateMe(payload: MeUpdate): Promise<Me> {
		return http.request<Me>('/me', { method: 'PATCH', body: payload });
	}

	function isAuthenticated(): boolean {
		return tokenStore.getAccessToken() !== null;
	}

	return { onboardAdmin, login, logout, requestMagicLink, verifyMagicLink, getMe, updateMe, isAuthenticated };
}

export type UserApi = ReturnType<typeof createUserApi>;
