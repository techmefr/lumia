export type Role = 'admin' | 'member';
export type Theme = 'light' | 'dark' | 'system';
export type OrbitPosition = 'left' | 'right';
export type AIProvider = 'mistral' | 'openai' | 'anthropic' | 'gemma' | 'custom';
export type TranslationProvider = 'deepl';
/** The reading language, which the backend translates foreign articles into. */
export type PreferredLanguage =
	| 'fr'
	| 'en'
	| 'es'
	| 'de'
	| 'it'
	| 'pt'
	| 'ru'
	| 'ar'
	| 'zh'
	| 'mg';

/** What a magic link was asked for, which decides the screen its email lands on. */
export type MagicLinkPurpose = 'sign_in' | 'password_reset';

/**
 * What a reader offers when their account asks for a second factor: a six-digit code from the
 * authenticator, or one of the recovery codes handed out at enrolment. Never both.
 */
export interface SecondFactor {
	totp_code?: string;
	recovery_code?: string;
}

/** The draft secret, in the two forms an authenticator takes: scanned, or typed by hand. */
export interface TotpEnrolment {
	secret: string;
	otpauth_uri: string;
}

export interface TotpRecoveryCodes {
	recovery_codes: string[];
}

/** Why a sign-in was refused, when it was refused for the second factor rather than the first. */
export type SecondFactorFailure = 'totp_required' | 'invalid_totp_code';

export interface TokenPair {
	access_token: string;
	refresh_token: string;
	token_type: string;
}

export interface Me {
	id: string;
	email: string;
	username: string;
	role: Role;
	/** Whether a password can be changed or has yet to be set: SSO accounts have none. */
	password_set: boolean;
	totp_enabled: boolean;
	/** How many recovery codes are still good, so a reader down to their last can be warned. */
	recovery_codes_left: number;
	theme: Theme;
	orbit_position: OrbitPosition;
	font_base_size: number;
	preferred_language: PreferredLanguage;
	ai_provider: AIProvider | null;
	ai_endpoint_url: string | null;
	ai_model: string | null;
	/** The keys never come back from the API, only whether one is on file. */
	ai_api_key_set: boolean;
	translation_provider: TranslationProvider | null;
	translation_api_key_set: boolean;
}

export interface MeUpdate {
	theme?: Theme;
	orbit_position?: OrbitPosition;
	font_base_size?: number;
	preferred_language?: PreferredLanguage;
	ai_provider?: AIProvider | null;
	/** An empty string or null removes the stored key. */
	ai_api_key?: string | null;
	ai_endpoint_url?: string | null;
	ai_model?: string | null;
	translation_provider?: TranslationProvider | null;
	translation_api_key?: string | null;
}
