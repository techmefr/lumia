import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { fakeSpeechSynthesis } from '../../test-support/fake-speech-synthesis';
import { articleDetail, articleSummary } from '../../src/routes/test-support/fixtures';
import { player } from './audio-player.svelte';
import PlayerBar from './player-bar.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		article: { getArticle: vi.fn() },
		recommendation: { sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

function bar() {
	const { container } = render(PlayerBar);
	const q = <T extends Element>(name: string) => container.querySelector<T>(`[data-test-${name}]`);
	return {
		root: () => q('player'),
		title: () => q<HTMLAnchorElement>('player-title'),
		toggle: () => q<HTMLButtonElement>('player-toggle'),
		next: () => q<HTMLButtonElement>('player-next'),
		previous: () => q<HTMLButtonElement>('player-previous'),
		close: () => q<HTMLButtonElement>('player-close'),
		expand: () => q<HTMLButtonElement>('player-expand'),
		details: () => q('player-details'),
		seek: () => q<HTMLInputElement>('player-seek'),
		rate: (value: number) => q<HTMLInputElement>(`player-rate="${value}"`),
		status: () => q('player-status')
	};
}

beforeEach(() => {
	fakeSpeechSynthesis();
	localStorage.clear();
	api.article.getArticle.mockResolvedValue(articleDetail('a', { content: '<p>Corps.</p>' }));
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
});

afterEach(() => {
	player.close();
	cleanup();
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('the player bar', () => {
	it('renders nothing while the queue is empty', () => {
		expect(bar().root()).toBeNull();
	});

	it('shows the article being read and announces it', async () => {
		await player.play([articleSummary('a', { title: 'Le papier' })]);
		const view = bar();

		expect(view.title()?.textContent).toContain('Le papier');
		expect(view.status()?.textContent).toContain('Le papier');
	});

	it('pauses and resumes from the main button', async () => {
		await player.play([articleSummary('a')]);
		const view = bar();

		await fireEvent.click(view.toggle()!);
		expect(player.paused).toBe(true);

		await fireEvent.click(view.toggle()!);
		expect(player.playing).toBe(true);
	});

	it('moves through the queue and disables the ends', async () => {
		await player.play([articleSummary('a'), articleSummary('b')]);
		const view = bar();

		expect(view.previous()?.disabled).toBe(true);
		await fireEvent.click(view.next()!);
		await vi.waitFor(() => expect(player.current?.id).toBe('b'));
		expect(view.next()?.disabled).toBe(true);
	});

	it('scrubs through the article from the slider', async () => {
		await player.play([articleSummary('a')]);
		const view = bar();
		const seek = vi.spyOn(player, 'seek');

		await fireEvent.input(view.seek()!, { target: { value: '40' } });

		expect(seek).toHaveBeenCalledWith(0.4);
		expect(view.seek()?.getAttribute('aria-label')).not.toBeNull();
	});

	it('expands to show the details and the speed choices', async () => {
		await player.play([articleSummary('a', { category_name: 'Science' })]);
		const view = bar();
		expect(view.details()).toBeNull();

		await fireEvent.click(view.expand()!);

		expect(view.expand()?.getAttribute('aria-expanded')).toBe('true');
		expect(view.details()?.textContent).toContain('Science');
		await fireEvent.click(view.rate(1.5)!);
		expect(player.rate).toBe(1.5);
	});

	it('closes and disappears', async () => {
		await player.play([articleSummary('a')]);
		const view = bar();

		await fireEvent.click(view.close()!);

		expect(view.root()).toBeNull();
	});
});
