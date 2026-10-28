import { cleanup, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import { setLocale } from '$technical/i18n/i18n.svelte';
import { connectivity } from '$technical/offline/connectivity.svelte';
import OfflineBanner from './offline-banner.svelte';

afterEach(() => {
	cleanup();
	connectivity.online = true;
});

describe('the offline banner', () => {
	it('says nothing while the network is there', () => {
		const { container } = render(OfflineBanner);

		expect(container.querySelector('[data-test-offline-banner]')).toBeNull();
	});

	it('announces that the reader is offline and what stays readable', async () => {
		setLocale('fr');
		connectivity.online = false;

		const { container } = render(OfflineBanner);

		const banner = container.querySelector('[data-test-offline-banner]');
		expect(banner).toHaveAttribute('role', 'status');
		expect(banner).toHaveTextContent(/hors ligne/i);
		expect(banner).toHaveTextContent(/liste à lire/i);
	});
});
