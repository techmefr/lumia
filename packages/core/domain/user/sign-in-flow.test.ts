import { describe, expect, it } from 'vitest';
import { ApiError, type HttpClient } from '../../technical/http-client';
import type { TokenStore } from '../../technical/token-store';
import { createUserApi } from './api';
import { createSignInFlow } from './sign-in-flow';

const TOKENS = { access_token: 'access-1', refresh_token: 'refresh-1' };

function backend(accepts: { totp?: string; recovery?: string }) {
	const bodies: Record<string, unknown>[] = [];
	const stored: string[] = [];
	const store = { setTokens: (t) => stored.push(t.accessToken) } as TokenStore;
	const http = {
		async request(path: string, options: { body?: Record<string, unknown> } = {}) {
			const body = options.body ?? {};
			bodies.push(body);
			if (body.password === 'wrong') throw new ApiError(401, { detail: 'invalid_credentials' });
			const proven =
				(body.totp_code !== undefined && body.totp_code === accepts.totp) ||
				(body.recovery_code !== undefined && body.recovery_code === accepts.recovery);
			if (proven) return TOKENS;
			if (body.totp_code !== undefined || body.recovery_code !== undefined)
				throw new ApiError(401, { detail: 'invalid_totp_code' });
			throw new ApiError(401, { detail: 'totp_required' });
		}
	} as unknown as HttpClient;
	return { bodies, stored, flow: createSignInFlow(createUserApi(http, store)) };
}

describe('sign-in flow', () => {
	it('moves to the code step when the account has a second factor, instead of failing', async () => {
		const { flow, stored } = backend({ totp: '123456' });
		expect(await flow.signIn('a@b.test', 'pw')).toBe('challenge');
		expect(flow.step).toBe('code');
		expect(stored).toEqual([]);
	});

	it('retries with the same credentials plus the code and signs in', async () => {
		const { flow, bodies, stored } = backend({ totp: '123456' });
		await flow.signIn('a@b.test', 'pw');
		expect(await flow.submitSecondFactor(' 123456 ')).toBe('signed_in');
		expect(bodies[1]).toEqual({ email: 'a@b.test', password: 'pw', totp_code: '123456' });
		expect(stored).toEqual(['access-1']);
		expect(flow.step).toBe('credentials');
	});

	it('reports a wrong code without dropping the challenge', async () => {
		const { flow } = backend({ totp: '123456' });
		await flow.signIn('a@b.test', 'pw');
		expect(await flow.submitSecondFactor('000000')).toBe('wrong_code');
		expect(flow.step).toBe('code');
	});

	it('lets a recovery code in when the authenticator is lost', async () => {
		const { flow, bodies } = backend({ recovery: 'abcd-efgh' });
		await flow.signIn('a@b.test', 'pw');
		flow.toggleRecovery();
		expect(flow.step).toBe('recovery');
		expect(await flow.submitSecondFactor('abcd-efgh')).toBe('signed_in');
		expect(bodies[1]).toEqual({ email: 'a@b.test', password: 'pw', recovery_code: 'abcd-efgh' });
	});

	it('toggles back from recovery to the code step', async () => {
		const { flow } = backend({});
		await flow.signIn('a@b.test', 'pw');
		flow.toggleRecovery();
		flow.toggleRecovery();
		expect(flow.step).toBe('code');
	});

	it('does not toggle before any challenge', () => {
		const { flow } = backend({});
		flow.toggleRecovery();
		expect(flow.step).toBe('credentials');
	});

	it('keeps a wrong password apart from a second-factor failure', async () => {
		const { flow } = backend({ totp: '123456' });
		expect(await flow.signIn('a@b.test', 'wrong')).toBe('bad_credentials');
		expect(flow.step).toBe('credentials');
		expect(() => flow.submitSecondFactor('123456')).toThrow();
	});

	it('challenges a magic link the same way', async () => {
		const { flow, bodies } = backend({ totp: '123456' });
		expect(await flow.signInWithMagicLink('tok')).toBe('challenge');
		expect(await flow.submitSecondFactor('123456')).toBe('signed_in');
		expect(bodies[1]).toEqual({ token: 'tok', totp_code: '123456' });
	});

	it('reports a non-401 failure as failed', async () => {
		const http = { request: async () => { throw new ApiError(500, null); } } as unknown as HttpClient;
		const flow = createSignInFlow(createUserApi(http, {} as TokenStore));
		expect(await flow.signIn('a@b.test', 'pw')).toBe('failed');
	});
});
