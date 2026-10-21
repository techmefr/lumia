import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { ApiError } from '@lumia/core';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import PlaylistSharing from './playlist-sharing.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { getMe: vi.fn() },
		playlist: { listMembers: vi.fn(), shareWith: vi.fn(), removeMember: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

const ADA = { user_id: 'user-ada', username: 'ada', role: 'editor' as const };

function sharing(role: 'owner' | 'editor' | 'viewer', onleave = vi.fn()) {
	const { container } = render(PlaylistSharing, { playlistId: 'list-1', role, onleave });
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		onleave,
		form: () => q<HTMLFormElement>('[data-test-share-form]'),
		members: () => [...container.querySelectorAll('[data-test-member]')],
		remove: (id: string) => q<HTMLButtonElement>(`[data-test-remove-member="${id}"]`),
		leave: () => q<HTMLButtonElement>('[data-test-leave]'),
		error: () => q('[data-test-sharing-error]'),
		submit: async (email: string, role?: string) => {
			await fireEvent.input(q('#share-email')!, { target: { value: email } });
			if (role) await fireEvent.change(q('#share-role')!, { target: { value: role } });
			await fireEvent.submit(q('[data-test-share-form]')!);
		}
	};
}

beforeEach(() => {
	api.user.getMe.mockResolvedValue({ id: 'me' } as Awaited<ReturnType<typeof api.user.getMe>>);
	api.playlist.listMembers.mockResolvedValue({ owner_name: 'admin', members: [ADA] });
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('for the owner', () => {
	it('lists the members and offers to share and to remove', async () => {
		const view = sharing('owner');
		await waitFor(() => expect(view.members()).toHaveLength(1));
		expect(view.form()).not.toBeNull();
		expect(view.remove('user-ada')).not.toBeNull();
		expect(view.leave()).toBeNull();
	});

	it('shares with the typed email and the chosen role, then shows the new list', async () => {
		api.playlist.shareWith.mockResolvedValue({
			owner_name: 'admin',
			members: [ADA, { user_id: 'user-bob', username: 'bob', role: 'viewer' }]
		});
		const view = sharing('owner');
		await waitFor(() => expect(view.members()).toHaveLength(1));

		await view.submit('bob@example.com', 'editor');

		await waitFor(() => expect(view.members()).toHaveLength(2));
		expect(api.playlist.shareWith).toHaveBeenCalledWith('list-1', 'bob@example.com', 'editor');
	});

	it('tells the owner when nobody on the instance has that email', async () => {
		api.playlist.shareWith.mockRejectedValue(new ApiError(404, {}));
		const view = sharing('owner');
		await waitFor(() => expect(view.members()).toHaveLength(1));

		await view.submit('nobody@example.com');

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('tells the owner when they try to share with themselves', async () => {
		api.playlist.shareWith.mockRejectedValue(new ApiError(422, {}));
		const view = sharing('owner');
		await waitFor(() => expect(view.members()).toHaveLength(1));

		await view.submit('admin@example.com');

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('removes a member and reloads the list', async () => {
		api.playlist.removeMember.mockResolvedValue(undefined);
		const view = sharing('owner');
		await waitFor(() => expect(view.members()).toHaveLength(1));
		api.playlist.listMembers.mockResolvedValue({ owner_name: 'admin', members: [] });

		await fireEvent.click(view.remove('user-ada')!);

		await waitFor(() => expect(view.members()).toHaveLength(0));
		expect(api.playlist.removeMember).toHaveBeenCalledWith('list-1', 'user-ada');
	});
});

describe('for a member', () => {
	it.each(['editor', 'viewer'] as const)(
		'shows a %s who is in, with no form and no removal of others',
		async (role) => {
			const view = sharing(role);
			await waitFor(() => expect(view.members()).toHaveLength(1));
			expect(view.form()).toBeNull();
			expect(view.remove('user-ada')).toBeNull();
			expect(view.leave()).not.toBeNull();
		}
	);

	it('leaves by removing themselves, then hands over', async () => {
		api.playlist.removeMember.mockResolvedValue(undefined);
		const view = sharing('viewer');
		await waitFor(() => expect(view.leave()).not.toBeNull());

		await fireEvent.click(view.leave()!);

		await waitFor(() => expect(view.onleave).toHaveBeenCalled());
		expect(api.playlist.removeMember).toHaveBeenCalledWith('list-1', 'me');
	});

	it('says so when leaving fails', async () => {
		api.playlist.removeMember.mockRejectedValue(new Error('boom'));
		const view = sharing('viewer');
		await waitFor(() => expect(view.leave()).not.toBeNull());

		await fireEvent.click(view.leave()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.onleave).not.toHaveBeenCalled();
	});
});

it('says so when the members cannot be loaded', async () => {
	api.playlist.listMembers.mockRejectedValue(new Error('boom'));
	const view = sharing('owner');
	await waitFor(() => expect(view.error()).not.toBeNull());
});
