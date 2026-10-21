import { toasts } from '@lumia/ui';
import { ApiError } from '@lumia/core';
import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { setLocale } from '$technical/i18n/i18n.svelte';
import ShareArticleButton from './share-article-button.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { article: { getShareStatus: vi.fn(), createShare: vi.fn(), revokeShare: vi.fn() } }
}));

const api = vi.mocked(lumia.article);

type Props = Parameters<typeof ShareArticleButton>[1];

function widget() {
	const { container } = render(ShareArticleButton, { articleId: 'article-1' } as Props);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		toggle: () => q<HTMLButtonElement>('[data-test-share-toggle]')!,
		panel: () => q('[data-test-share-panel]'),
		disabled: () => q('[data-test-share-disabled]'),
		active: () => q('[data-test-share-active]'),
		link: () => q<HTMLInputElement>('[data-test-share-link]'),
		create: () => q<HTMLButtonElement>('[data-test-share-create]'),
		revoke: () => q<HTMLButtonElement>('[data-test-share-revoke]'),
		copy: () => q<HTMLButtonElement>('[data-test-share-copy]'),
		error: () => q('[data-test-share-error]'),
		open: async function () {
			await fireEvent.click(this.toggle());
			await waitFor(() => expect(q('[data-test-share-loading]')).toBeNull());
		}
	};
}

beforeEach(() => {
	setLocale('fr');
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	api.getShareStatus.mockResolvedValue({ enabled: true, shared: false, created_at: null });
});

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('the sharing panel', () => {
	it('stays closed, and asks nothing, until the reader opens it', () => {
		const view = widget();

		expect(view.panel()).toBeNull();
		expect(view.toggle().getAttribute('aria-expanded')).toBe('false');
		expect(api.getShareStatus).not.toHaveBeenCalled();
	});

	it('reads the status of its own article when opened', async () => {
		const view = widget();

		await view.open();

		expect(api.getShareStatus).toHaveBeenCalledWith('article-1');
		expect(view.toggle().getAttribute('aria-expanded')).toBe('true');
		expect(view.create()).not.toBeNull();
		expect(view.revoke()).toBeNull();
	});

	it('says sharing is off, and offers nothing to create, when the admin has not allowed it', async () => {
		api.getShareStatus.mockResolvedValue({ enabled: false, shared: false, created_at: null });
		const view = widget();

		await view.open();

		expect(view.disabled()).not.toBeNull();
		expect(view.create()).toBeNull();
	});

	it('reports a status it could not read', async () => {
		api.getShareStatus.mockRejectedValue(new Error('down'));
		const view = widget();

		await view.open();

		expect(view.error()).not.toBeNull();
	});

	it('closes again on a second click without asking twice', async () => {
		const view = widget();
		await view.open();

		await fireEvent.click(view.toggle());
		await fireEvent.click(view.toggle());

		expect(view.panel()).not.toBeNull();
		expect(api.getShareStatus).toHaveBeenCalledTimes(1);
	});
});

describe('creating a link', () => {
	it('shows the link built on the page address and the token it was given', async () => {
		api.createShare.mockResolvedValue({ token: 'tok-123', created_at: '2026-10-21T10:00:00Z' });
		const view = widget();
		await view.open();

		await fireEvent.click(view.create()!);

		await waitFor(() => expect(view.link()).not.toBeNull());
		expect(api.createShare).toHaveBeenCalledWith('article-1');
		expect(view.link()?.value).toBe(`${window.location.origin}/share/tok-123`);
		expect(view.revoke()).not.toBeNull();
	});

	it('copies the link and says so', async () => {
		const writeText = vi.fn().mockResolvedValue(undefined);
		vi.stubGlobal('navigator', { clipboard: { writeText } });
		api.createShare.mockResolvedValue({ token: 'tok-123', created_at: '2026-10-21T10:00:00Z' });
		const view = widget();
		await view.open();
		await fireEvent.click(view.create()!);
		await waitFor(() => expect(view.copy()).not.toBeNull());

		await fireEvent.click(view.copy()!);

		await waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(writeText).toHaveBeenCalledWith(`${window.location.origin}/share/tok-123`);
	});

	it('turns into the disabled notice when the instance refuses', async () => {
		api.createShare.mockRejectedValue(new ApiError(403, { detail: 'public_sharing_disabled' }));
		const view = widget();
		await view.open();

		await fireEvent.click(view.create()!);

		await waitFor(() => expect(view.disabled()).not.toBeNull());
		expect(view.error()).not.toBeNull();
	});

	it('reports any other failure and keeps the button available', async () => {
		api.createShare.mockRejectedValue(new Error('down'));
		const view = widget();
		await view.open();

		await fireEvent.click(view.create()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.create()).not.toBeNull();
	});
});

describe('an article that already has a link', () => {
	beforeEach(() => {
		api.getShareStatus.mockResolvedValue({
			enabled: true,
			shared: true,
			created_at: '2026-10-20T10:00:00Z'
		});
	});

	it('says a link is live without being able to show it again', async () => {
		const view = widget();

		await view.open();

		expect(view.active()).not.toBeNull();
		expect(view.link()).toBeNull();
	});

	it('revokes it and goes back to offering a new one', async () => {
		api.revokeShare.mockResolvedValue(undefined);
		const view = widget();
		await view.open();

		await fireEvent.click(view.revoke()!);

		await waitFor(() => expect(view.revoke()).toBeNull());
		expect(api.revokeShare).toHaveBeenCalledWith('article-1');
		expect(view.active()).toBeNull();
		await waitFor(() => expect(toasts.toasts).toHaveLength(1));
	});

	it('keeps the link when the revocation fails, and says so', async () => {
		api.revokeShare.mockRejectedValue(new Error('down'));
		const view = widget();
		await view.open();

		await fireEvent.click(view.revoke()!);

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.revoke()).not.toBeNull();
	});
});
