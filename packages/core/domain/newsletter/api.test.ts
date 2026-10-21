import { describe, expect, it } from 'vitest';
import { recordingHttpClient } from '../../test-support/recording-http-client';
import { createNewsletterApi } from './api';

function api(replies: unknown[] = [{}]) {
	const recorder = recordingHttpClient(replies);
	return { ...recorder, newsletter: createNewsletterApi(recorder.http) };
}

describe('the newsletter inbox', () => {
	it('reads whether an address is live', async () => {
		const { newsletter, last } = api([{ active: true, created_at: '2026-10-21T10:00:00Z' }]);
		await expect(newsletter.getInboxStatus()).resolves.toEqual({
			active: true,
			created_at: '2026-10-21T10:00:00Z'
		});
		expect(last()).toMatchObject({
			path: '/newsletters/inbox',
			method: 'GET',
			auth: true
		});
	});

	it('issues an address with a POST and returns its token', async () => {
		const { newsletter, last } = api([{ token: 'secret', created_at: '2026-10-21T10:00:00Z' }]);
		await expect(newsletter.createInbox()).resolves.toMatchObject({
			token: 'secret'
		});
		expect(last()).toMatchObject({
			path: '/newsletters/inbox',
			method: 'POST'
		});
	});

	it('closes the address with a DELETE', async () => {
		const { newsletter, last } = api([undefined]);
		await newsletter.revokeInbox();
		expect(last()).toMatchObject({
			path: '/newsletters/inbox',
			method: 'DELETE'
		});
	});
});
