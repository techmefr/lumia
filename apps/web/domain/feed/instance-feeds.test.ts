import type { Feed, InstanceFeed } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import InstanceFeeds from './instance-feeds.svelte';

// The client is the app's http boundary, so it is what gets replaced.
vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { feed: { listInstanceFeeds: vi.fn(), attachInstanceFeeds: vi.fn() } }
}));

const api = vi.mocked(lumia.feed);

type Props = Parameters<typeof InstanceFeeds>[1];

const CANDIDATES: InstanceFeed[] = [
	{
		external_feed_id: '42',
		title: 'LWN.net',
		url: 'https://lwn.net/headlines/rss',
		category: 'Linux'
	},
	{
		external_feed_id: '43',
		title: 'Hacker News',
		url: 'https://hnrss.org/frontpage',
		category: null
	}
];

function attached(externalFeedId: string): Feed {
	return {
		id: `feed-${externalFeedId}`,
		folder_id: null,
		source_type: 'miniflux',
		external_feed_id: externalFeedId,
		title: 'Whatever',
		url: 'https://whatever.test/rss'
	};
}

function instanceFeeds(overrides: Partial<Props> = {}) {
	const onAttached = vi.fn();
	const { container } = render(InstanceFeeds, { onAttached, ...overrides } as Props);

	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		onAttached,
		loading: () => q('[data-test-instance-loading]'),
		error: () => q('[data-test-instance-error]'),
		empty: () => q('[data-test-instance-empty]'),
		selectAll: () => q<HTMLInputElement>('[data-test-instance-select-all]')!,
		attach: () => q<HTMLButtonElement>('[data-test-instance-attach]')!,
		items: () => [...container.querySelectorAll<HTMLElement>('[data-test-instance-feed]')],
		item: (id: string) => q<HTMLElement>(`[data-test-instance-feed="${id}"]`),
		checkbox: (id: string) =>
			q<HTMLInputElement>(`[data-test-instance-feed="${id}"] [data-test-instance-checkbox]`)!,
		category: (id: string) =>
			q<HTMLElement>(`[data-test-instance-feed="${id}"] [data-test-instance-category]`)!
	};
}

async function loaded(overrides: Partial<Props> = {}) {
	const view = instanceFeeds(overrides);
	await vi.waitFor(() => expect(view.loading()).toBeNull());
	return view;
}

beforeEach(() => {
	api.listInstanceFeeds.mockResolvedValue(CANDIDATES);
	api.attachInstanceFeeds.mockReset();
	api.attachInstanceFeeds.mockResolvedValue([attached('42')]);
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.clearAllMocks();
});

describe('listing what the instance carries', () => {
	it('asks for it on its own', async () => {
		await loaded();
		expect(api.listInstanceFeeds).toHaveBeenCalledTimes(1);
	});

	it('announces the wait', async () => {
		api.listInstanceFeeds.mockReturnValue(new Promise(() => {}));
		const view = instanceFeeds();

		expect(view.loading()?.getAttribute('role')).toBe('status');
		expect(view.loading()?.getAttribute('aria-label')).toBeTruthy();
	});

	it('lists one row per feed', async () => {
		const view = await loaded();
		expect(view.items()).toHaveLength(2);
	});

	// The category is how a reader recognises a feed among fifty: it is what Miniflux filed it
	// under, and what the folder will be named once attached.
	it('shows the miniflux category of each feed', async () => {
		const view = await loaded();
		expect(view.category('42').textContent).toContain('Linux');
	});

	it('says so rather than showing an empty badge for a feed filed nowhere', async () => {
		const view = await loaded();
		expect(view.category('43').textContent?.trim()).toBeTruthy();
	});

	it('says so when the instance could not be read', async () => {
		api.listInstanceFeeds.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		expect(view.error()?.getAttribute('role')).toBe('alert');
	});

	// An empty answer means every feed of the instance is already followed, which is worth saying.
	it('says there is nothing left to pick up rather than showing a blank panel', async () => {
		api.listInstanceFeeds.mockResolvedValue([]);
		const view = await loaded();

		expect(view.empty()).not.toBeNull();
	});
});

describe('choosing which feeds to follow', () => {
	it('starts with nothing ticked, so a click never subscribes to the lot', async () => {
		const view = await loaded();

		expect(view.checkbox('42').checked).toBe(false);
		expect(view.attach().disabled).toBe(true);
	});

	it('ticks and unticks a single feed', async () => {
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		expect(view.checkbox('42').checked).toBe(true);

		await fireEvent.click(view.checkbox('42'));
		expect(view.checkbox('42').checked).toBe(false);
	});

	it('ticks every feed at once, and clears them the same way', async () => {
		const view = await loaded();

		await fireEvent.click(view.selectAll());
		expect(view.items().every((_, index) => view.checkbox(CANDIDATES[index].external_feed_id).checked)).toBe(
			true
		);

		await fireEvent.click(view.selectAll());
		expect(view.checkbox('43').checked).toBe(false);
	});

	it('attaches only what was ticked', async () => {
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		expect(api.attachInstanceFeeds).toHaveBeenCalledWith(['42']);
	});
});

describe('attaching', () => {
	it('takes the attached feeds off the list without reloading', async () => {
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		await vi.waitFor(() => expect(view.item('42')).toBeNull());
		expect(view.item('43')).not.toBeNull();
		expect(api.listInstanceFeeds).toHaveBeenCalledTimes(1);
	});

	// A feed the backend could not attach stays on the list: the reader has to be able to retry it.
	it('keeps a feed the backend did not attach', async () => {
		api.attachInstanceFeeds.mockResolvedValue([]);
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(view.item('42')).not.toBeNull();
	});

	it('confirms it', async () => {
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('default');
	});

	// The caller owns the sidebar and the folder list, which the new folders just changed.
	it('tells the page around it to refresh', async () => {
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		await vi.waitFor(() => expect(view.onAttached).toHaveBeenCalledTimes(1));
	});

	it('disables the button while it is working, so the selection cannot be sent twice', async () => {
		api.attachInstanceFeeds.mockReturnValue(new Promise(() => {}));
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		await vi.waitFor(() => expect(view.attach().disabled).toBe(true));
	});

	it('keeps the selection and says so when it failed', async () => {
		api.attachInstanceFeeds.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
		expect(view.checkbox('42').checked).toBe(true);
		expect(view.onAttached).not.toHaveBeenCalled();
	});

	it('re-enables the button after a failure', async () => {
		api.attachInstanceFeeds.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.click(view.checkbox('42'));
		await fireEvent.click(view.attach());

		await vi.waitFor(() => expect(view.attach().disabled).toBe(false));
	});
});
