import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createFakeExtension } from '$test-support/fake-extension';
import { stubFetch, TOKENS } from '$test-support/stub-fetch';
import { en } from '$technical/i18n/messages/en';
import AccountPanel from './account-panel.svelte';

const INSTANCE = 'https://lumia.test';

afterEach(() => {
	vi.unstubAllGlobals();
});

async function fillCredentials() {
	await userEvent.type(await screen.findByLabelText(en['login.email']), 'ada@example.com');
	await userEvent.type(screen.getByLabelText(en['login.password']), 'secret-pass');
	await userEvent.click(screen.getByRole('button', { name: en['login.submit'] }));
}

describe('AccountPanel', () => {
	it('asks for the instance address before offering a sign-in', () => {
		const fake = createFakeExtension();
		render(AccountPanel, { extension: fake.extension, instanceUrl: null });
		expect(screen.getByText(en['settings.needInstance'])).toBeInTheDocument();
		expect(screen.queryByLabelText(en['login.email'])).toBeNull();
	});

	it('signs in with the credentials and keeps the tokens in the extension storage', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': INSTANCE } });
		const { requests } = stubFetch([{ status: 200, body: TOKENS }]);
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });

		await fillCredentials();

		expect(await screen.findByText(en['settings.signedIn'])).toBeInTheDocument();
		expect(requests[0]).toMatchObject({
			url: 'https://lumia.test/api/auth/login',
			body: { email: 'ada@example.com', password: 'secret-pass' }
		});
		expect(fake.store['lumia.access_token']).toBe('access-1');
		expect(fake.store['lumia.refresh_token']).toBe('refresh-1');
	});

	it('shows the session as open when tokens are already stored', async () => {
		const fake = createFakeExtension({
			stored: {
				'lumia.instance_url': INSTANCE,
				'lumia.access_token': 'a',
				'lumia.refresh_token': 'r'
			}
		});
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });
		expect(await screen.findByText(en['settings.signedIn'])).toBeInTheDocument();
	});

	it('names a wrong password instead of a generic failure', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': INSTANCE } });
		stubFetch([{ status: 401, body: { detail: 'invalid_credentials' } }]);
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });

		await fillCredentials();

		expect(await screen.findByRole('alert')).toHaveTextContent(en['login.badCredentials']);
		expect(fake.store['lumia.access_token']).toBeUndefined();
	});

	it('reports an unreachable instance as a failure, not as a wrong password', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': INSTANCE } });
		stubFetch([{ status: 500 }]);
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });

		await fillCredentials();

		expect(await screen.findByRole('alert')).toHaveTextContent(en['login.failed']);
	});

	it('asks for the authenticator code, then signs in with it', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': INSTANCE } });
		const { requests } = stubFetch([
			{ status: 401, body: { detail: 'totp_required' } },
			{ status: 200, body: TOKENS }
		]);
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });

		await fillCredentials();
		await userEvent.type(await screen.findByLabelText(en['login.totpCode']), '123456');
		await userEvent.click(screen.getByRole('button', { name: en['login.totpSubmit'] }));

		expect(await screen.findByText(en['settings.signedIn'])).toBeInTheDocument();
		expect(requests[1].body).toEqual({
			email: 'ada@example.com',
			password: 'secret-pass',
			totp_code: '123456'
		});
	});

	it('says a wrong code is wrong, and lets a recovery code replace it', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': INSTANCE } });
		const { requests } = stubFetch([
			{ status: 401, body: { detail: 'totp_required' } },
			{ status: 401, body: { detail: 'invalid_totp_code' } },
			{ status: 200, body: TOKENS }
		]);
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });

		await fillCredentials();
		await userEvent.type(await screen.findByLabelText(en['login.totpCode']), '000000');
		await userEvent.click(screen.getByRole('button', { name: en['login.totpSubmit'] }));
		expect(await screen.findByRole('alert')).toHaveTextContent(en['login.totpInvalid']);

		await userEvent.click(screen.getByRole('button', { name: en['login.useRecovery'] }));
		expect(screen.queryByRole('alert')).toBeNull();
		await userEvent.type(screen.getByLabelText(en['login.recoveryCode']), 'abcd-efgh');
		await userEvent.click(screen.getByRole('button', { name: en['login.totpSubmit'] }));

		expect(await screen.findByText(en['settings.signedIn'])).toBeInTheDocument();
		expect(requests[2].body).toMatchObject({ recovery_code: 'abcd-efgh' });
	});

	it('goes back from the recovery code to the authenticator code', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': INSTANCE } });
		stubFetch([{ status: 401, body: { detail: 'totp_required' } }]);
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });

		await fillCredentials();
		await userEvent.click(await screen.findByRole('button', { name: en['login.useRecovery'] }));
		await userEvent.click(screen.getByRole('button', { name: en['login.backToCode'] }));

		expect(screen.getByLabelText(en['login.totpCode'])).toBeInTheDocument();
	});

	it('signs out: the tokens leave the extension storage even before the server answers', async () => {
		const fake = createFakeExtension({
			stored: {
				'lumia.instance_url': INSTANCE,
				'lumia.access_token': 'a',
				'lumia.refresh_token': 'r'
			}
		});
		const { requests } = stubFetch([{ status: 204 }]);
		render(AccountPanel, { extension: fake.extension, instanceUrl: INSTANCE });

		await userEvent.click(await screen.findByRole('button', { name: en['settings.signOut'] }));

		expect(await screen.findByLabelText(en['login.email'])).toBeInTheDocument();
		expect(requests[0]).toMatchObject({
			url: 'https://lumia.test/api/auth/logout',
			body: { refresh_token: 'r' }
		});
		expect(fake.store['lumia.access_token']).toBeUndefined();
		expect(fake.store['lumia.refresh_token']).toBeUndefined();
	});
});
