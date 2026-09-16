import { ApiError } from '@lumia/core';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import OnboardingPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { user: { onboardAdmin: vi.fn() } }
}));

const api = vi.mocked(lumia.user, { deep: true });

function onboardingPage() {
	const { container } = render(OnboardingPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		form: () => q<HTMLFormElement>('form')!,
		email: () => q<HTMLInputElement>('#email')!,
		username: () => q<HTMLInputElement>('#username')!,
		password: () => q<HTMLInputElement>('#password')!,
		error: () => q('[role="alert"]')
	};
}

async function submitted() {
	const view = onboardingPage();
	await fireEvent.input(view.email(), { target: { value: 'admin@example.test' } });
	await fireEvent.input(view.username(), { target: { value: 'camille' } });
	await fireEvent.input(view.password(), { target: { value: 'un-mot-de-passe' } });
	await fireEvent.submit(view.form());
	return view;
}

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('claiming a fresh instance', () => {
	it('creates the first administrator and opens the article list', async () => {
		api.onboardAdmin.mockResolvedValue(undefined);

		await submitted();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(api.onboardAdmin).toHaveBeenCalledWith({
			email: 'admin@example.test',
			username: 'camille',
			password: 'un-mot-de-passe'
		});
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/articles');
	});

	// An instance that already has an administrator answers 409, and that is a different problem
	// from a request that simply failed: there is nothing to claim, not something to retry.
	it('says the instance is already claimed on a conflict', async () => {
		api.onboardAdmin.mockRejectedValue(new ApiError(409, 'conflict'));

		const view = await submitted();

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(goto).not.toHaveBeenCalled();
	});

	it('reports any other failure without leaving the form', async () => {
		api.onboardAdmin.mockRejectedValue(new Error('offline'));

		const view = await submitted();

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.form()).not.toBeNull();
		expect(goto).not.toHaveBeenCalled();
	});
});
