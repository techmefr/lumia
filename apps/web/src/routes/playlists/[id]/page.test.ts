import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { fakeSpeechSynthesis, type FakeSynthesis } from '../../../../test-support/fake-speech-synthesis';
import { articleDetail, articleSummary, playlistDetail } from '../../test-support/fixtures';
import PlaylistPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

let params: Record<string, string> = { id: 'list-1' };
vi.mock('$app/state', () => ({
	page: {
		get params() {
			return params;
		}
	}
}));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		article: { getArticle: vi.fn() },
		playlist: { getPlaylist: vi.fn(), reorder: vi.fn(), removeArticle: vi.fn() },
		recommendation: { sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

let engine: FakeSynthesis;

function playlistPage() {
	const { container } = render(PlaylistPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loading: () => q('[role="status"]'),
		error: () => q('[role="alert"]'),
		heading: () => q('h1'),
		rows: () => [...container.querySelectorAll('ol > li')],
		titles: () =>
			[...container.querySelectorAll('ol > li a > span:first-child')].map(
				(span) => span.textContent ?? ''
			),
		rowButtons: (index: number) =>
			[...(container.querySelectorAll('ol > li')[index]?.querySelectorAll('button') ?? [])],
		nowPlaying: () => q('[aria-live="polite"]'),
		browse: () => q<HTMLAnchorElement>('a[href$="/articles"]')
	};
}

/** The listen / move-up / move-down / remove buttons of a row, in the order the page lays them out. */
const LISTEN = 0;
const MOVE_UP = 1;
const MOVE_DOWN = 2;
const REMOVE = 3;

async function loaded(articles = [articleSummary('a'), articleSummary('b')]) {
	api.playlist.getPlaylist.mockResolvedValue(playlistDetail('list-1', articles));
	const view = playlistPage();
	await waitFor(() => expect(view.loading()).toBeNull());
	return view;
}

beforeEach(() => {
	params = { id: 'list-1' };
	engine = fakeSpeechSynthesis();
	api.user.isAuthenticated.mockReturnValue(true);
	api.playlist.getPlaylist.mockResolvedValue(playlistDetail('list-1', [articleSummary('a')]));
	api.article.getArticle.mockResolvedValue(articleDetail('a', { content: '<p>Le corps.</p>' }));
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
});

afterEach(() => {
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('opening a playlist', () => {
	it('lists the articles it holds', async () => {
		const view = await loaded();

		expect(view.rows()).toHaveLength(2);
		expect(api.playlist.getPlaylist).toHaveBeenCalledWith('list-1');
	});

	it('points an empty playlist at the article list', async () => {
		const view = await loaded([]);

		expect(view.rows()).toHaveLength(0);
		expect(view.browse()).not.toBeNull();
	});

	it('says the playlist cannot be found when the request fails', async () => {
		api.playlist.getPlaylist.mockRejectedValue(new Error('gone'));
		const view = playlistPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('asks for nothing when the route carries no id', async () => {
		params = {};
		const view = playlistPage();

		await waitFor(() => expect(view.error()).not.toBeNull());
		expect(api.playlist.getPlaylist).not.toHaveBeenCalled();
	});
});

describe('reading the playlist aloud', () => {
	it('fetches the body and reads it after the title', async () => {
		const view = await loaded([articleSummary('a', { title: 'Le papier' })]);

		await fireEvent.click(view.rowButtons(0)[LISTEN]);

		await waitFor(() => expect(engine.spoken.length).toBeGreaterThan(0));
		expect(api.article.getArticle).toHaveBeenCalledWith('a');
		expect(engine.spoken[0].text).toContain('Le papier');
		expect(engine.spoken.map((utterance) => utterance.text).join(' ')).toContain('Le corps.');
	});

	it('marks an article read once it has been read out', async () => {
		const view = await loaded([articleSummary('a')]);

		await fireEvent.click(view.rowButtons(0)[LISTEN]);

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { read: true })
		);
	});

	// The list carries only a summary, so a body that cannot be fetched still has something to read
	// rather than silently skipping the article.
	it('falls back on the summary when the body cannot be fetched', async () => {
		api.article.getArticle.mockRejectedValue(new Error('offline'));
		const view = await loaded([articleSummary('a', { summary: 'Un résumé court.' })]);

		await fireEvent.click(view.rowButtons(0)[LISTEN]);

		await waitFor(() => expect(engine.spoken.length).toBeGreaterThan(0));
		expect(engine.spoken[0].text).toContain('Un résumé court.');
	});

	it('chains to the next article on its own', async () => {
		const view = await loaded([articleSummary('a'), articleSummary('b', { title: 'Le suivant' })]);
		api.article.getArticle.mockResolvedValue(articleDetail('b', { content: '<p>Suite.</p>' }));
		await fireEvent.click(view.rowButtons(0)[LISTEN]);
		await waitFor(() => expect(engine.spoken.length).toBeGreaterThan(0));

		while (engine.current()) engine.finish();

		await waitFor(() =>
			expect(engine.spoken.map((utterance) => utterance.text).join(' ')).toContain('Le suivant')
		);
	});

	it('announces which article is being read', async () => {
		const view = await loaded([articleSummary('a', { title: 'Le papier' })]);

		await fireEvent.click(view.rowButtons(0)[LISTEN]);

		await waitFor(() => expect(view.nowPlaying()?.textContent).toContain('Le papier'));
	});

	it('stops announcing anything once the playlist runs out', async () => {
		const view = await loaded([articleSummary('a')]);
		await fireEvent.click(view.rowButtons(0)[LISTEN]);
		await waitFor(() => expect(view.nowPlaying()).not.toBeNull());

		while (engine.current()) engine.finish();

		await waitFor(() => expect(view.nowPlaying()).toBeNull());
	});
});

describe('rearranging a playlist', () => {
	it('swaps an article with the one below it', async () => {
		const view = await loaded([articleSummary('a'), articleSummary('b')]);
		api.playlist.reorder.mockResolvedValue(
			playlistDetail('list-1', [articleSummary('b'), articleSummary('a')])
		);

		await fireEvent.click(view.rowButtons(0)[MOVE_DOWN]);

		await waitFor(() => expect(api.playlist.reorder).toHaveBeenCalledWith('list-1', ['b', 'a']));
		await waitFor(() => expect(view.titles()[0]).toContain('Titre b'));
	});

	it('swaps an article with the one above it', async () => {
		const view = await loaded([articleSummary('a'), articleSummary('b')]);
		api.playlist.reorder.mockResolvedValue(
			playlistDetail('list-1', [articleSummary('b'), articleSummary('a')])
		);

		await fireEvent.click(view.rowButtons(1)[MOVE_UP]);

		await waitFor(() => expect(api.playlist.reorder).toHaveBeenCalledWith('list-1', ['b', 'a']));
	});

	// The ends have nowhere to go, and a request that swapped nothing would reorder the list to
	// itself while looking like it worked.
	it('cannot move the first article up or the last one down', async () => {
		const view = await loaded([articleSummary('a'), articleSummary('b')]);

		expect(view.rowButtons(0)[MOVE_UP].disabled).toBe(true);
		expect(view.rowButtons(1)[MOVE_DOWN].disabled).toBe(true);
	});

	it('keeps the order on screen when the reorder fails', async () => {
		const view = await loaded([articleSummary('a'), articleSummary('b')]);
		api.playlist.reorder.mockRejectedValue(new Error('offline'));

		await fireEvent.click(view.rowButtons(0)[MOVE_DOWN]);

		await waitFor(() => expect(api.playlist.reorder).toHaveBeenCalled());
		expect(view.titles()[0]).toContain('Titre a');
	});
});

describe('removing an article from a playlist', () => {
	it('drops it from the list', async () => {
		const view = await loaded([articleSummary('a'), articleSummary('b')]);
		api.playlist.removeArticle.mockResolvedValue(playlistDetail('list-1', [articleSummary('b')]));

		await fireEvent.click(view.rowButtons(0)[REMOVE]);

		await waitFor(() =>
			expect(api.playlist.removeArticle).toHaveBeenCalledWith('list-1', 'a')
		);
		await waitFor(() => expect(view.rows()).toHaveLength(1));
	});

	it('leaves the list alone when the removal fails', async () => {
		const view = await loaded([articleSummary('a'), articleSummary('b')]);
		api.playlist.removeArticle.mockRejectedValue(new Error('offline'));

		await fireEvent.click(view.rowButtons(0)[REMOVE]);

		await waitFor(() => expect(api.playlist.removeArticle).toHaveBeenCalled());
		expect(view.rows()).toHaveLength(2);
	});
});
