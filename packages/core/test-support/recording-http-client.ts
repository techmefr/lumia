import type { HttpClient, RequestOptions } from '../technical/http-client';

export interface RecordedRequest {
	path: string;
	method: string;
	body: unknown;
	formData: FormData | undefined;
	auth: boolean;
}

/**
 * An HttpClient that records what it was asked for and answers with a queued reply.
 *
 * The api modules exist to turn arguments into one request; that request is their observable
 * output, the same way a header is for the real client. Recording it is what lets the assertions
 * be about the path, verb and payload the backend will actually receive.
 */
export function recordingHttpClient(replies: unknown[] = []) {
	const requests: RecordedRequest[] = [];
	const queue = [...replies];

	const http: HttpClient = {
		async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
			requests.push({
				path,
				method: options.method ?? 'GET',
				body: options.body,
				formData: options.formData,
				auth: options.auth ?? true
			});
			return queue.shift() as T;
		}
	};

	return { http, requests, last: () => requests[requests.length - 1] };
}
