import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import FeverSettings from './fever-settings.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: {
			getFeverKey: vi.fn(),
			createFeverKey: vi.fn(),
			revokeFeverKey: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.user);

const OFF = { enabled: false, created_at: null as string | null };
const ON = { enabled: true, created_at: '2026-10-21T10:00:00Z' };
const CREATED = {
	email: 'lecteur@example.test',
	secret: 'a-long-random-secret-shown-once',
	created_at: '2026-10-21T10:00:00Z'
};

function panel() {
	const { container } = render(FeverSettings);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		status: () => q('[data-test-fever-status]'),
		create: () => q<HTMLButtonElement>('[data-test-fever-create]'),
		revoke: () => q<HTMLButtonElement>('[data-test-fever-revoke]'),
		credentials: () => q('[data-test-fever-credentials]'),
		field: (name: string) => q<HTMLInputElement>(`[data-test-fever-field="${name}"]`),
		done: () => q<HTMLButtonElement>('[data-test-fever-done]'),
		error: () => q('[data-test-fever-error]')
	};
}

async function loaded(status = OFF) {
	api.getFeverKey.mockResolvedValue(status);
	const view = panel();
	await vi.waitFor(() => expect(view.status()).not.toBeNull());
	await vi.waitFor(() => expect(view.revoke() !== null).toBe(status.enabled));
	return view;
}

beforeEach(() => {
	api.getFeverKey.mockReset();
	api.createFeverKey.mockReset();
	api.revokeFeverKey.mockReset();
});

afterEach(() => {
	vi.clearAllMocks();
});

describe('a reader without a key', () => {
	it('offers to create one and shows nothing secret', async () => {
		const view = await loaded();

		expect(view.create()).not.toBeNull();
		expect(view.revoke()).toBeNull();
		expect(view.credentials()).toBeNull();
	});

	it('shows the address, the login and the secret once the key is created', async () => {
		const view = await loaded();
		api.createFeverKey.mockResolvedValue(CREATED);
		api.getFeverKey.mockResolvedValue(ON);

		await fireEvent.click(view.create()!);

		await vi.waitFor(() => expect(view.credentials()).not.toBeNull());
		expect(view.field('endpoint')?.value).toMatch(/\/fever\/$/);
		expect(view.field('username')?.value).toBe(CREATED.email);
		expect(view.field('secret')?.value).toBe(CREATED.secret);
	});

	it('hands the secret over in read-only fields with their own labels', async () => {
		const view = await loaded();
		api.createFeverKey.mockResolvedValue(CREATED);
		api.getFeverKey.mockResolvedValue(ON);
		await fireEvent.click(view.create()!);
		await vi.waitFor(() => expect(view.credentials()).not.toBeNull());

		const secret = view.field('secret')!;

		expect(secret.readOnly).toBe(true);
		expect(document.querySelector(`label[for="${secret.id}"]`)).not.toBeNull();
	});

	it('forgets the secret once the reader says it is copied', async () => {
		const view = await loaded();
		api.createFeverKey.mockResolvedValue(CREATED);
		api.getFeverKey.mockResolvedValue(ON);
		await fireEvent.click(view.create()!);
		await vi.waitFor(() => expect(view.credentials()).not.toBeNull());

		await fireEvent.click(view.done()!);

		await vi.waitFor(() => expect(view.credentials()).toBeNull());
		expect(document.body.textContent).not.toContain(CREATED.secret);
		expect(view.revoke()).not.toBeNull();
	});

	it('says so and keeps the offer when the creation fails', async () => {
		const view = await loaded();
		api.createFeverKey.mockRejectedValue(new Error('boom'));

		await fireEvent.click(view.create()!);

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.credentials()).toBeNull();
		expect(view.create()).not.toBeNull();
	});
});

describe('a reader who already has a key', () => {
	it('can replace it or revoke it, and never sees the old secret', async () => {
		const view = await loaded(ON);

		expect(view.create()).not.toBeNull();
		expect(view.revoke()).not.toBeNull();
		expect(view.credentials()).toBeNull();
	});

	it('revokes it on request', async () => {
		const view = await loaded(ON);
		api.revokeFeverKey.mockResolvedValue(undefined);
		api.getFeverKey.mockResolvedValue(OFF);

		await fireEvent.click(view.revoke()!);

		await vi.waitFor(() => expect(api.revokeFeverKey).toHaveBeenCalledTimes(1));
		await vi.waitFor(() => expect(view.revoke()).toBeNull());
		expect(view.create()).not.toBeNull();
	});

	it('keeps the key and says so when the revocation fails', async () => {
		const view = await loaded(ON);
		api.revokeFeverKey.mockRejectedValue(new Error('boom'));

		await fireEvent.click(view.revoke()!);

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.revoke()).not.toBeNull();
	});
});
