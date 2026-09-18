import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import type { ArticleSummary } from '@lumia/core';
import { articleSummary } from '../test-support/fixtures';
import EtincellePage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: { isAuthenticated: vi.fn(() => true) },
		recommendation: { getEtincelle: vi.fn(), sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

function etincellePage() {
	const { container } = render(EtincellePage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		loading: () => q('[role="status"]'),
		error: () => q('[role="alert"]'),
		topCard: () => q('[data-test-swipe-card="top"]'),
		notEnough: () => q('a[href$="/articles"]'),
		like: () => q<HTMLButtonElement>('[data-test-swipe-like]')!,
		dislike: () => q<HTMLButtonElement>('[data-test-swipe-dislike]')!,
		save: () => q<HTMLButtonElement>('[data-test-swipe-save]')!,
		favorite: () => q<HTMLButtonElement>('[data-test-swipe-favorite]')!,
		open: () => q<HTMLButtonElement>('[data-test-swipe-open]')!
	};
}

async function withStack(articles = [articleSummary('a'), articleSummary('b')]) {
	api.recommendation.getEtincelle.mockResolvedValue(articles);
	const view = etincellePage();
	await waitFor(() => expect(view.topCard()).not.toBeNull());
	return view;
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.recommendation.getEtincelle.mockResolvedValue([articleSummary('a')]);
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
});

afterEach(() => {
	cleanup();
	vi.clearAllMocks();
});

describe('opening the etincelle stack', () => {
	it('shows a placeholder while the selection is being built', async () => {
		let release: (value: ArticleSummary[]) => void = () => {};
		api.recommendation.getEtincelle.mockReturnValue(new Promise((resolve) => (release = resolve)));

		const view = etincellePage();

		expect(view.loading()).not.toBeNull();
		release([articleSummary('a')]);
		await waitFor(() => expect(view.topCard()).not.toBeNull());
	});

	// Etincelle needs a pool to draw from; with none, the way out is subscribing, not retrying.
	it('sends the reader to the article list when there is nothing to draw from', async () => {
		api.recommendation.getEtincelle.mockResolvedValue([]);
		const view = etincellePage();

		await waitFor(() => expect(view.notEnough()).not.toBeNull());
		expect(view.topCard()).toBeNull();
	});

	it('says so when the selection cannot be fetched', async () => {
		api.recommendation.getEtincelle.mockRejectedValue(new Error('offline'));
		const view = etincellePage();

		await waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		etincellePage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(api.recommendation.getEtincelle).not.toHaveBeenCalled();
	});
});

describe('voting on the top card', () => {
	it('records a like and moves on to the next article', async () => {
		const view = await withStack();

		await fireEvent.click(view.like());

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { sentiment: 'like' })
		);
	});

	it('records a dislike and moves on as well', async () => {
		const view = await withStack();

		await fireEvent.click(view.dislike());

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { sentiment: 'dislike' })
		);
	});

	// Saving is not a verdict, so the card stays on the pile and can still be voted on.
	it('keeps the card on the pile when it is only saved', async () => {
		const view = await withStack();

		await fireEvent.click(view.save());

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { saved: true })
		);
		expect(view.topCard()).not.toBeNull();
	});

	it('marks the top card as a favourite without dismissing it', async () => {
		const view = await withStack();

		await fireEvent.click(view.favorite());

		await waitFor(() =>
			expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { favorite: true })
		);
		expect(view.topCard()).not.toBeNull();
	});

	it('congratulates the reader once every card has been voted on', async () => {
		const view = await withStack([articleSummary('a')]);

		await fireEvent.click(view.like());

		await waitFor(() => expect(view.topCard()).toBeNull());
		expect(view.notEnough()).toBeNull();
	});

	it('opens the article the reader asks to read in full', async () => {
		const view = await withStack();

		await fireEvent.click(view.open());

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls.at(-1)?.[0])).toContain('/articles/a');
	});
});
