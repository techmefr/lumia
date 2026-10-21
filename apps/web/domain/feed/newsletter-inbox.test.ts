import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import NewsletterInbox from './newsletter-inbox.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		newsletter: {
			getInboxStatus: vi.fn(),
			createInbox: vi.fn(),
			revokeInbox: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.newsletter);

function view() {
	const { container } = render(NewsletterInbox);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		create: () => q<HTMLButtonElement>('[data-test-newsletters-create]')!,
		revoke: () => q<HTMLButtonElement>('[data-test-newsletters-revoke]'),
		address: () => q<HTMLInputElement>('[data-test-newsletters-address]'),
		active: () => q('[data-test-newsletters-active]'),
		error: () => q('[data-test-newsletters-error]')
	};
}

beforeEach(() => {
	api.getInboxStatus.mockReset();
	api.createInbox.mockReset();
	api.revokeInbox.mockReset();
});

afterEach(cleanup);

describe('the newsletter inbox card', () => {
	it('offers to create an address when none is live', async () => {
		api.getInboxStatus.mockResolvedValue({ active: false, created_at: null });
		const page = view();

		await waitFor(() => expect(page.create().disabled).toBe(false));

		expect(page.revoke()).toBeNull();
		expect(page.address()).toBeNull();
	});

	it('shows the address once after creating it, built on the app origin', async () => {
		api.getInboxStatus.mockResolvedValue({ active: false, created_at: null });
		api.createInbox.mockResolvedValue({
			token: 'tok123',
			created_at: '2026-10-21T10:00:00Z'
		});
		const page = view();
		await waitFor(() => expect(page.create().disabled).toBe(false));

		await fireEvent.click(page.create());

		await waitFor(() => expect(page.address()).not.toBeNull());
		expect(page.address()!.value).toBe(`${window.location.origin}/api/inbound/newsletters/tok123`);
		expect(page.revoke()).not.toBeNull();
	});

	it('says the address is live without being able to show it again', async () => {
		api.getInboxStatus.mockResolvedValue({
			active: true,
			created_at: '2026-10-21T10:00:00Z'
		});
		const page = view();

		await waitFor(() => expect(page.active()).not.toBeNull());

		expect(page.address()).toBeNull();
	});

	it('closes the address on request', async () => {
		api.getInboxStatus.mockResolvedValue({
			active: true,
			created_at: '2026-10-21T10:00:00Z'
		});
		api.revokeInbox.mockResolvedValue(undefined);
		const page = view();
		await waitFor(() => expect(page.revoke()).not.toBeNull());

		await fireEvent.click(page.revoke()!);

		await waitFor(() => expect(page.revoke()).toBeNull());
		expect(api.revokeInbox).toHaveBeenCalledOnce();
		expect(page.active()).toBeNull();
	});

	it('reports a failed creation instead of showing an address', async () => {
		api.getInboxStatus.mockResolvedValue({ active: false, created_at: null });
		api.createInbox.mockRejectedValue(new Error('boom'));
		const page = view();
		await waitFor(() => expect(page.create().disabled).toBe(false));

		await fireEvent.click(page.create());

		await waitFor(() => expect(page.error()).not.toBeNull());
		expect(page.address()).toBeNull();
	});

	it('reports a status that could not be read', async () => {
		api.getInboxStatus.mockRejectedValue(new Error('down'));
		const page = view();

		await waitFor(() => expect(page.error()).not.toBeNull());
	});
});
