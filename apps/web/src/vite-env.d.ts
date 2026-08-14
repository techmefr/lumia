/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_API_BASE_URL: string;
	/** "true" in the static demo build: the api client is replaced by an in-memory one. */
	readonly VITE_DEMO?: string;
}
