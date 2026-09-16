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

/** How often a reader asked to be mailed a digest; `never` is the only default we may assume. */
export type DigestFrequency = 'never' | 'daily' | 'weekly';

/** What a magic link was asked for, which decides the screen its email lands on. */
export type MagicLinkPurpose = 'sign_in' | 'password_reset';

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
	theme: Theme;
	orbit_position: OrbitPosition;
	font_base_size: number;
	preferred_language: PreferredLanguage;
	digest_frequency: DigestFrequency;
	/** Hour of the day, 0-23, read in `digest_timezone` rather than in UTC. */
	digest_hour: number;
	/** An IANA zone name, "Europe/Paris". */
	digest_timezone: string;
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
	digest_frequency?: DigestFrequency;
	digest_hour?: number;
	digest_timezone?: string;
	ai_provider?: AIProvider | null;
	/** An empty string or null removes the stored key. */
	ai_api_key?: string | null;
	ai_endpoint_url?: string | null;
	ai_model?: string | null;
	translation_provider?: TranslationProvider | null;
	translation_api_key?: string | null;
}
