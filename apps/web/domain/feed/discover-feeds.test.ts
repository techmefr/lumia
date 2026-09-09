import type { DiscoverSuggestion, Folder } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import DiscoverFeeds from './discover-feeds.svelte';

// The client is the app's http boundary, so it is what gets replaced.
vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { feed: { discoverFeeds: vi.fn(), addFeedByUrl: vi.fn() } }
}));

const api = vi.mocked(lumia.feed);

type Props = Parameters<typeof DiscoverFeeds>[1];

function suggestion(
	url: string,
	overrides: Partial<DiscoverSuggestion> = {}
): DiscoverSuggestion {
	return {
		url,
		title: `Flux ${url}`,
		description: 'Une description courte.',
		site_url: `https://site.test/${url}`,
		language: 'fr',
		topics: ['presse', 'papier'],
		affinity: null,
		...overrides
	} as DiscoverSuggestion;
}

const SUGGESTIONS = [suggestion('https://a.test/rss'), suggestion('https://b.test/rss')];

const FOLDERS: Folder[] = [
	{ id: 'folder-news', name: 'Actualités' },
	{ id: 'folder-tech', name: 'Technique' }
];

function discover(overrides: Partial<Props> = {}) {
	const onSubscribed = vi.fn();
	const { container } = render(DiscoverFeeds, {
		folders: FOLDERS,
		onSubscribed,
		...overrides
	} as Props);

	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		onSubscribed,
		loading: () => q('[data-test-discover-loading]'),
		error: () => q('[data-test-discover-error]'),
		exhausted: () => q('[data-test-discover-exhausted]'),
		refresh: () => q<HTMLButtonElement>('[data-test-discover-refresh]')!,
		folder: () => q<HTMLSelectElement>('[data-test-discover-folder]'),
		items: () => [...container.querySelectorAll<HTMLElement>('[data-test-suggestion]')],
		item: (url: string) => q<HTMLElement>(`[data-test-suggestion="${url}"]`),
		subscribeIn: (url: string) =>
			q<HTMLButtonElement>(`[data-test-suggestion="${url}"] [data-test-subscribe]`)!
	};
}

async function loaded(overrides: Partial<Props> = {}) {
	const view = discover(overrides);
	await vi.waitFor(() => expect(view.loading()).toBeNull());
	return view;
}

beforeEach(() => {
	api.discoverFeeds.mockResolvedValue(SUGGESTIONS);
	api.addFeedByUrl.mockReset();
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.clearAllMocks();
});

describe('loading the suggestions', () => {
	it('asks for them on its own', async () => {
		await loaded();
		expect(api.discoverFeeds).toHaveBeenCalledTimes(1);
	});

	// Placeholders shaped like the cards to come, and announced: the list arrives from a scoring
	// pass on the backend and is not instant.
	it('announces the wait', async () => {
		api.discoverFeeds.mockReturnValue(new Promise(() => {}));
		const view = discover();

		expect(view.loading()?.getAttribute('role')).toBe('status');
		expect(view.loading()?.getAttribute('aria-label')).toBeTruthy();
	});

	it('lists one entry per suggestion', async () => {
		const view = await loaded();
		expect(view.items()).toHaveLength(2);
	});

	it('says so when nothing could be loaded', async () => {
		api.discoverFeeds.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		expect(view.error()?.getAttribute('role')).toBe('alert');
	});

	// Everything already subscribed is filtered out by the backend, so an empty answer means the
	// reader has taken the lot. That is worth saying rather than showing a blank panel.
	it('says the list is exhausted rather than showing nothing', async () => {
		api.discoverFeeds.mockResolvedValue([]);
		const view = await loaded();

		expect(view.exhausted()).not.toBeNull();
	});

	it('asks again when refreshed', async () => {
		const view = await loaded();

		await fireEvent.click(view.refresh());

		await vi.waitFor(() => expect(api.discoverFeeds).toHaveBeenCalledTimes(2));
	});

	it('clears a previous error when the refresh works', async () => {
		api.discoverFeeds.mockRejectedValueOnce(new Error('offline'));
		api.discoverFeeds.mockResolvedValueOnce(SUGGESTIONS);
		const view = await loaded();
		expect(view.error()).not.toBeNull();

		await fireEvent.click(view.refresh());

		await vi.waitFor(() => expect(view.error()).toBeNull());
	});
});

describe('what a suggestion shows', () => {
	it('names it and describes it', async () => {
		const view = await loaded();
		const first = view.item('https://a.test/rss')!;

		expect(first.textContent).toContain('Flux https://a.test/rss');
		expect(first.textContent).toContain('Une description courte.');
	});

	it('shows its language and its topics', async () => {
		const view = await loaded();
		const first = view.item('https://a.test/rss')!;

		expect(first.textContent).toContain('fr');
		expect(first.textContent).toContain('presse');
		expect(first.textContent).toContain('papier');
	});

	// The affinity is the reason a suggestion is near the top: it is computed from what the reader
	// has liked. A suggestion with none is a plain suggestion, and a badge saying nothing would be
	// worse than no badge.
	it('shows the affinity when there is one', async () => {
		api.discoverFeeds.mockResolvedValue([suggestion('https://a.test/rss', { affinity: 42 })]);
		const view = await loaded();

		expect(view.container.querySelector('[data-test-suggestion-affinity]')?.textContent).toContain(
			'42'
		);
	});

	it('shows no affinity badge when there is none', async () => {
		const view = await loaded();

		expect(view.container.querySelector('[data-test-suggestion-affinity]')).toBeNull();
	});

	it('links to the site, in a new tab, with a name of its own', async () => {
		const view = await loaded();
		const link = view.item('https://a.test/rss')!.querySelector('[data-test-suggestion-site]')!;

		expect(link.getAttribute('href')).toBe('https://site.test/https://a.test/rss');
		expect(link.getAttribute('target')).toBe('_blank');
		expect(link.querySelector('.sr-only')?.textContent).toBeTruthy();
	});
});

describe('choosing where a new feed lands', () => {
	it('offers each folder, plus staying unfiled', async () => {
		const view = await loaded();

		expect([...view.folder()!.options].map((option) => option.value)).toEqual([
			'',
			'folder-news',
			'folder-tech'
		]);
	});

	it('leaves a new feed unfiled by default', async () => {
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		expect(api.addFeedByUrl).toHaveBeenCalledWith('https://a.test/rss', null);
	});

	it('files it into the folder that was chosen', async () => {
		const view = await loaded();

		await fireEvent.change(view.folder()!, { target: { value: 'folder-tech' } });
		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		expect(api.addFeedByUrl).toHaveBeenCalledWith('https://a.test/rss', 'folder-tech');
	});

	// No folders means no choice to make: the select would be a control with one option.
	it('offers no folder picker when there is no folder', async () => {
		const view = await loaded({ folders: [] });

		expect(view.folder()).toBeNull();
	});
});

describe('subscribing', () => {
	it('adds the feed that was chosen', async () => {
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://b.test/rss'));

		expect(api.addFeedByUrl).toHaveBeenCalledWith('https://b.test/rss', null);
	});

	// Dropped from the list rather than refetched: the backend already excludes what is subscribed,
	// so a reload would do the same thing one round trip later and flash the whole panel.
	it('takes it off the list without reloading', async () => {
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		await vi.waitFor(() => expect(view.item('https://a.test/rss')).toBeNull());
		expect(view.items()).toHaveLength(1);
		expect(api.discoverFeeds).toHaveBeenCalledTimes(1);
	});

	it('confirms it', async () => {
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('default');
	});

	// The caller owns the sidebar and the folder counts, which are now wrong: it has to be told.
	it('tells the page around it to refresh', async () => {
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		await vi.waitFor(() => expect(view.onSubscribed).toHaveBeenCalledTimes(1));
	});

	it('disables the button while it is working, so it cannot be pressed twice', async () => {
		api.addFeedByUrl.mockReturnValue(new Promise(() => {}));
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		await vi.waitFor(() => expect(view.subscribeIn('https://a.test/rss').disabled).toBe(true));
		expect(view.subscribeIn('https://b.test/rss').disabled).toBe(false);
	});

	it('keeps the suggestion and says so when it failed', async () => {
		api.addFeedByUrl.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
		expect(view.item('https://a.test/rss')).not.toBeNull();
	});

	it('does not tell the page to refresh when nothing was added', async () => {
		api.addFeedByUrl.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(view.onSubscribed).not.toHaveBeenCalled();
	});

	// A failure must leave the button pressable again, or a network blip means reloading the page.
	it('re-enables the button after a failure', async () => {
		api.addFeedByUrl.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.click(view.subscribeIn('https://a.test/rss'));

		await vi.waitFor(() => expect(view.subscribeIn('https://a.test/rss').disabled).toBe(false));
	});
});
