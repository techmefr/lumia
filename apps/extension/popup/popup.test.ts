import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createFakeExtension } from '$test-support/fake-extension';
import { stubFetch } from '$test-support/stub-fetch';
import { en } from '$technical/i18n/messages/en';
import Popup from './popup.svelte';

const SIGNED_IN = {
	'lumia.instance_url': 'https://lumia.test',
	'lumia.access_token': 'access',
	'lumia.refresh_token': 'refresh'
};

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('Popup', () => {
	it('saves the current tab as soon as it opens and says so', async () => {
		const fake = createFakeExtension({
			stored: SIGNED_IN,
			tabs: [{ url: 'https://blog.test/post' }]
		});
		const { requests } = stubFetch([{ status: 201, body: { id: 'a', already_saved: false } }]);
		render(Popup, { extension: fake.extension });

		expect(await screen.findByText(en['save.saved'])).toBeInTheDocument();
		expect(requests[0].body).toEqual({ url: 'https://blog.test/post' });
		expect(screen.getByRole('status')).toHaveTextContent(en['save.saved']);
		expect(screen.queryByRole('button')).toBeNull();
	});

	it('shows a status while the page is being saved', () => {
		const fake = createFakeExtension({ stored: SIGNED_IN, tabs: [{ url: 'https://blog.test/' }] });
		stubFetch([]);
		render(Popup, { extension: fake.extension });
		expect(screen.getByRole('status')).toHaveTextContent(en['save.saving']);
	});

	it('says the page is already there instead of saving it twice', async () => {
		const fake = createFakeExtension({
			stored: SIGNED_IN,
			tabs: [{ url: 'https://blog.test/post' }]
		});
		stubFetch([{ status: 201, body: { id: 'a', already_saved: true } }]);
		render(Popup, { extension: fake.extension });
		expect(await screen.findByText(en['save.alreadySaved'])).toBeInTheDocument();
	});

	it('announces a failure as an alert', async () => {
		const fake = createFakeExtension({
			stored: SIGNED_IN,
			tabs: [{ url: 'https://blog.test/post' }]
		});
		stubFetch([{ status: 400 }]);
		render(Popup, { extension: fake.extension });
		expect(await screen.findByRole('alert')).toHaveTextContent(en['save.failed']);
		expect(screen.queryByRole('button')).toBeNull();
	});

	it('leads to the settings when there is no instance yet', async () => {
		const fake = createFakeExtension({ tabs: [{ url: 'https://blog.test/post' }] });
		render(Popup, { extension: fake.extension });

		const button = await screen.findByRole('button', { name: en['popup.openSettings'] });
		await userEvent.click(button);
		expect(fake.optionsPageOpened()).toBe(1);
	});

	it('refuses a page the extension cannot save', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN, tabs: [{ url: 'chrome://extensions' }] });
		render(Popup, { extension: fake.extension });
		expect(await screen.findByRole('alert')).toHaveTextContent(en['save.unsupported']);
	});
});
