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

export function stubRoutes(routes: Record<string, Reply | Reply[]>) {
	const requests: StubbedRequest[] = [];
	const remaining = new Map(
		Object.entries(routes).map(([key, value]) => [key, Array.isArray(value) ? [...value] : [value]])
	);

	vi.stubGlobal(
		'fetch',
		vi.fn(async (url: string, init: RequestInit = {}) => {
			const headers = new Headers(init.headers);
			const method = init.method ?? 'GET';
			const parsed = new URL(url);
			const key = `${method} ${parsed.pathname.replace(/^\/api/, '')}${parsed.search}`;
			requests.push({
				url,
				method,
				body: typeof init.body === 'string' ? JSON.parse(init.body) : undefined,
				authorization: headers.get('authorization')
			});
			const queue = remaining.get(key);
			if (queue === undefined) throw new Error(`unexpected request ${key}`);
			const reply = queue.length > 1 ? queue.shift()! : queue[0];
			if (reply instanceof Error) throw reply;
			return new Response(reply.body === undefined ? null : JSON.stringify(reply.body), {
				status: reply.status,
				headers: { 'content-type': 'application/json' }
			});
		})
	);

	return { requests };
}

export function articleSummary(overrides: Record<string, unknown> = {}) {
	return {
		id: 'article-1',
		feed_id: 'feed-1',
		author_id: null,
		author_name: null,
		category_id: null,
		category_name: null,
		source_label: 'Le Blog',
		title: 'A first article',
		url: 'https://blog.test/first',
		summary: null,
		image_url: null,
		enclosure_url: null,
		enclosure_type: null,
		published_at: '2026-10-01T08:00:00Z',
		reading_minutes: 4,
		read: false,
		scroll_progress: 0,
		relevance_score: 50,
		tags: [],
		...overrides
	};
}

export function feed(overrides: Record<string, unknown> = {}) {
	return {
		id: 'feed-1',
		folder_id: null,
		source_type: 'miniflux',
		external_feed_id: '1',
		title: 'Le Blog',
		url: 'https://blog.test/feed.xml',
		...overrides
	};
}
