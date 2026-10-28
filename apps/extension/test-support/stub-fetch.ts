import { vi } from 'vitest';

export interface StubbedRequest {
	url: string;
	method: string;
	body: unknown;
	authorization: string | null;
}

type Reply = { status: number; body?: unknown } | Error;

export function stubFetch(replies: Reply[]) {
	const requests: StubbedRequest[] = [];
	const queue = [...replies];

	vi.stubGlobal(
		'fetch',
		vi.fn(async (url: string, init: RequestInit = {}) => {
			const headers = new Headers(init.headers);
			requests.push({
				url,
				method: init.method ?? 'GET',
				body: typeof init.body === 'string' ? JSON.parse(init.body) : undefined,
				authorization: headers.get('authorization')
			});
			const reply = queue.shift();
			if (reply === undefined) throw new Error(`unexpected request ${url}`);
			if (reply instanceof Error) throw reply;
			return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), {
				status: reply.status,
				headers: { 'content-type': 'application/json' }
			});
		})
	);

	return { requests };
}

export const TOKENS = { access_token: 'access-1', refresh_token: 'refresh-1' };
