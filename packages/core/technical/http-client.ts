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
	const REJECTED_STATUSES = new Set([400, 401, 403]);
	let inFlightRefresh: Promise<string | null> | null = null;

	function isTokenPair(value: unknown): value is { access_token: string; refresh_token: string } {
		if (typeof value !== 'object' || value === null) return false;
		const candidate = value as Record<string, unknown>;
		return (
			typeof candidate.access_token === 'string' &&
			candidate.access_token !== '' &&
			typeof candidate.refresh_token === 'string' &&
			candidate.refresh_token !== ''
		);
	}

	async function performRefresh(): Promise<string | null> {
		const refreshToken = tokenStore.getRefreshToken();
		if (!refreshToken) return null;

		let response: Response;
		try {
			response = await fetch(`${baseUrl}/auth/refresh`, {
				method: 'POST',
				headers: { 'content-type': 'application/json' },
				body: JSON.stringify({ refresh_token: refreshToken })
			});
		} catch {
			return null;
		}
		if (!response.ok) {
			if (REJECTED_STATUSES.has(response.status)) tokenStore.clear();
			return null;
		}

		const payload: unknown = await response.json().catch(() => null);
		if (!isTokenPair(payload)) return null;

		tokenStore.setTokens({
			accessToken: payload.access_token,
			refreshToken: payload.refresh_token
		});
		return payload.access_token;
	}

	async function runExclusively(): Promise<string | null> {
		const staleAccessToken = tokenStore.getAccessToken();
		const attempt = async () => {
			await tokenStore.reload?.();
			const current = tokenStore.getAccessToken();
			if (current && current !== staleAccessToken) return current;
			return performRefresh();
		};
		return tokenStore.exclusive ? tokenStore.exclusive(attempt) : attempt();
	}

	function refreshAccessToken(): Promise<string | null> {
		inFlightRefresh ??= runExclusively().finally(() => {
			inFlightRefresh = null;
		});
		return inFlightRefresh;
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

	async function sendAuthenticated(
		path: string,
		options: RequestOptions
	): Promise<Response> {
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
		return response;
	}

	async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
		const response = await sendAuthenticated(path, options);
		if (response.status === 204) return undefined as T;
		return (await response.json()) as T;
	}

	/** For an endpoint that hands back a file (e.g. an OPML export) rather than JSON. */
	async function requestBlob(path: string, options: RequestOptions = {}): Promise<Blob> {
		const response = await sendAuthenticated(path, options);
		return await response.blob();
	}

	return { request, requestBlob };
}

export type HttpClient = ReturnType<typeof createHttpClient>;
