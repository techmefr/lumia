import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createFakeExtension } from '$test-support/fake-extension';
import { articleSummary, stubRoutes } from '$test-support/stub-fetch';
import { en } from '$technical/i18n/messages/en';
import Sidepanel from './sidepanel.svelte';

const SIGNED_IN = {
	'lumia.instance_url': 'https://lumia.test',
	'lumia.access_token': 'access',
	'lumia.refresh_token': 'refresh'
};

const LIST = 'GET /articles?limit=20&offset=0';

afterEach(() => {
	vi.unstubAllGlobals();
	window.location.hash = '';
});

describe('Sidepanel', () => {
	it('asks for the instance address when none is stored, and opens the settings', async () => {
		const fake = createFakeExtension();
		render(Sidepanel, { extension: fake.extension });

		expect(await screen.findByRole('alert')).toHaveTextContent(en['save.unconfigured']);
		await userEvent.click(screen.getByRole('button', { name: en['popup.openSettings'] }));
		expect(fake.optionsPageOpened()).toBe(1);
	});

	it('asks to sign in with the account the popup and settings share', async () => {
		const fake = createFakeExtension({ stored: { 'lumia.instance_url': 'https://lumia.test' } });
		render(Sidepanel, { extension: fake.extension });
		expect(await screen.findByRole('alert')).toHaveTextContent(en['save.unauthenticated']);
	});

	it('reads with the tokens the sign-in of the settings page stored', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN });
		const { requests } = stubRoutes({
			'GET /feeds': { status: 200, body: [] },
			[LIST]: { status: 200, body: [articleSummary({ title: 'In the panel' })] }
		});
		render(Sidepanel, { extension: fake.extension });

		expect(await screen.findByText('In the panel')).toBeInTheDocument();
		expect(requests.every((request) => request.authorization === 'Bearer access')).toBe(true);
	});

	it('opens an article from the list and comes back to the list', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN });
		stubRoutes({
			'GET /feeds': { status: 200, body: [] },
			[LIST]: { status: 200, body: [articleSummary({ id: 'a1', title: 'Open me' })] },
			'GET /articles/a1': {
				status: 200,
				body: { ...articleSummary({ id: 'a1', title: 'Open me' }), content: '<p>Inside</p>', keywords: [] }
			},
			'POST /articles/mark-read': { status: 200, body: { updated: 1 } }
		});
		render(Sidepanel, { extension: fake.extension });

		await userEvent.click(await screen.findByText('Open me'));
		expect(await screen.findByText('Inside')).toBeInTheDocument();

		await userEvent.click(screen.getByRole('link', { name: en['reader.back'] }));
		await waitFor(() => expect(screen.queryByText('Inside')).toBeNull());
		expect(await screen.findByText('Open me')).toBeInTheDocument();
	});

	it('goes back to the sign-in prompt when the session expires while reading', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN });
		stubRoutes({
			'GET /feeds': { status: 401 },
			[LIST]: { status: 401 },
			'POST /auth/refresh': { status: 401 }
		});
		render(Sidepanel, { extension: fake.extension });

		await waitFor(() =>
			expect(screen.getByRole('button', { name: en['popup.openSettings'] })).toBeInTheDocument()
		);
		expect(screen.getByText(en['save.unauthenticated'])).toBeInTheDocument();
	});
});
