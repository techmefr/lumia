import type { TokenStore } from './token-store';

export class ApiError extends Error {
	status: number;
	body: unknown;

	constructor(status: number, body: unknown) {
		super(`API error ${status}`);
		this.status = status;
		this.body = body;
	}
}

export interface HttpClientConfig {
	baseUrl: string;
	tokenStore: TokenStore;
}

export interface RequestOptions {
	method?: string;
	body?: unknown;
	formData?: FormData;
	/** Attach the bearer token and retry once via refresh on 401. Defaults to true. */
	auth?: boolean;
}

export function createHttpClient({ baseUrl, tokenStore }: HttpClientConfig) {
	async function refreshAccessToken(): Promise<string | null> {
		const refreshToken = tokenStore.getRefreshToken();
		if (!refreshToken) return null;

		const response = await fetch(`${baseUrl}/auth/refresh`, {
			method: 'POST',
			headers: { 'content-type': 'application/json' },
			body: JSON.stringify({ refresh_token: refreshToken })
		});
		if (!response.ok) {
			tokenStore.clear();
			return null;
		}

		const { access_token } = (await response.json()) as { access_token: string };
		tokenStore.setAccessToken(access_token);
		return access_token;
	}

	async function send(path: string, options: RequestOptions, accessToken: string | null) {
		const headers: Record<string, string> = {};
		if (accessToken) headers.authorization = `Bearer ${accessToken}`;

		let requestBody: BodyInit | undefined;
		if (options.formData) {
			requestBody = options.formData;
		} else if (options.body !== undefined) {
			headers['content-type'] = 'application/json';
			requestBody = JSON.stringify(options.body);
		}

		return fetch(`${baseUrl}${path}`, {
			method: options.method ?? 'GET',
			headers,
			body: requestBody
		});
	}

	async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
		const auth = options.auth ?? true;

		let accessToken = auth ? tokenStore.getAccessToken() : null;
		let response = await send(path, options, accessToken);

		if (auth && response.status === 401) {
			accessToken = await refreshAccessToken();
			if (accessToken) response = await send(path, options, accessToken);
		}

		if (!response.ok) {
			const errorBody = await response.json().catch(() => null);
			throw new ApiError(response.status, errorBody);
		}

		if (response.status === 204) return undefined as T;
		return (await response.json()) as T;
	}

	return { request };
}

export type HttpClient = ReturnType<typeof createHttpClient>;
