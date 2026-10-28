import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createFakeExtension } from '$test-support/fake-extension';
import { stubFetch, TOKENS } from '$test-support/stub-fetch';
import { en } from '$technical/i18n/messages/en';
import Settings from './settings.svelte';

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('Settings', () => {
	it('shows the stored instance address and a sign-in form', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': 'https://lumia.test' } });
		render(Settings, { extension: fake.extension });

		expect(await screen.findByLabelText(en['settings.instanceLabel'])).toHaveValue(
			'https://lumia.test'
		);
		expect(await screen.findByLabelText(en['login.email'])).toBeInTheDocument();
	});

	it('unlocks the sign-in once the address is saved, then signs in against it', async () => {
		const fake = createFakeExtension();
		const { requests } = stubFetch([{ status: 200, body: TOKENS }]);
		render(Settings, { extension: fake.extension });

		expect(await screen.findByText(en['settings.needInstance'])).toBeInTheDocument();
		await userEvent.type(
			screen.getByLabelText(en['settings.instanceLabel']),
			'https://lumia.example.com'
		);
		await userEvent.click(screen.getByRole('button', { name: en['settings.instanceSave'] }));

		await userEvent.type(await screen.findByLabelText(en['login.email']), 'ada@example.com');
		await userEvent.type(screen.getByLabelText(en['login.password']), 'secret-pass');
		await userEvent.click(screen.getByRole('button', { name: en['login.submit'] }));

		expect(await screen.findByText(en['settings.signedIn'])).toBeInTheDocument();
		expect(requests[0].url).toBe('https://lumia.example.com/api/auth/login');
	});
});
