export type Role = 'admin' | 'member';
export type Theme = 'light' | 'dark' | 'system';
export type OrbitPosition = 'left' | 'right';
export type AIProvider = 'mistral' | 'openai' | 'anthropic' | 'custom';
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
