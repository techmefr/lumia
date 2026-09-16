import { ApiError, type HttpClient } from '../../technical/http-client';
import type { TokenStore } from '../../technical/token-store';
import type {
	MagicLinkPurpose,
	Me,
	MeUpdate,
	SecondFactor,
	SecondFactorFailure,
	TokenPair,
	TotpEnrolment,
	TotpRecoveryCodes
} from './types';

/**
 * Reads why a 401 refused a sign-in, when it was the second factor and not the first.
 *
 * The backend answers `totp_required` apart from `invalid_totp_code` so the form knows whether to
 * ask for a code or to say the one it got is wrong. Anything else is a plain wrong credential.
 */
export function secondFactorFailure(error: unknown): SecondFactorFailure | null {
	if (!(error instanceof ApiError) || error.status !== 401) return null;
	const detail = (error.body as { detail?: unknown } | null)?.detail;
	return detail === 'totp_required' || detail === 'invalid_totp_code' ? detail : null;
}

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

	/**
	 * `secondFactor` is left out on the first try: the form has no way of knowing whether the
	 * account asks for one until the backend says so, and asking everybody up front would tell an
	 * unauthenticated caller which accounts have it turned on.
	 */
	async function login(
		email: string,
		password: string,
		secondFactor: SecondFactor = {}
	): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/auth/login', {
				method: 'POST',
				body: { email, password, ...secondFactor },
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

	/**
	 * A magic link proves control of the mailbox, which is exactly what the second factor is there
	 * to stop being enough, so an account that has one is challenged here too.
	 */
	async function verifyMagicLink(token: string, secondFactor: SecondFactor = {}): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/auth/magic-link/verify', {
				method: 'POST',
				body: { token, ...secondFactor },
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

	async function resetPassword(
		token: string,
		newPassword: string,
		secondFactor: SecondFactor = {}
	): Promise<void> {
		storeTokens(
			await http.request<TokenPair>('/auth/password-reset', {
				method: 'POST',
				body: { token, new_password: newPassword, ...secondFactor },
				auth: false
			})
		);
	}

	/** Draws a secret for an authenticator. Nothing is switched on until it is confirmed. */
	async function startTotpEnrolment(): Promise<TotpEnrolment> {
		return http.request<TotpEnrolment>('/me/totp/enrolment', { method: 'POST' });
	}

	/** Turns the second factor on, and hands back the recovery codes for the only time. */
	async function confirmTotpEnrolment(code: string): Promise<string[]> {
		const { recovery_codes } = await http.request<TotpRecoveryCodes>('/me/totp', {
			method: 'POST',
			body: { code }
		});
		return recovery_codes;
	}

	/** Replaces the whole set; the previous codes stop working straight away. */
	async function renewRecoveryCodes(code: string): Promise<string[]> {
		const { recovery_codes } = await http.request<TotpRecoveryCodes>('/me/totp/recovery-codes', {
			method: 'POST',
			body: { code }
		});
		return recovery_codes;
	}

	/** Re-authentication, not a setting: an access token alone must not undo the second factor. */
	async function disableTotp(password: string | null, secondFactor: SecondFactor = {}): Promise<void> {
		await http.request('/me/totp', {
			method: 'DELETE',
			body: { password, ...secondFactor }
		});
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
		startTotpEnrolment,
		confirmTotpEnrolment,
		renewRecoveryCodes,
		disableTotp,
		getMe,
		updateMe,
		isAuthenticated
	};
}

export type UserApi = ReturnType<typeof createUserApi>;
