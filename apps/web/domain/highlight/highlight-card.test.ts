import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Highlight } from '@lumia/core';
import { setLocale } from '$technical/i18n/i18n.svelte';
import HighlightCard from './highlight-card.svelte';

type Props = Parameters<typeof HighlightCard>[1];

function highlight(overrides: Partial<Highlight> = {}): Highlight {
	return {
		id: 'h1',
		article_id: 'article-1',
		article_title: 'Le papier et l encre',
		quote: 'le papier',
		prefix: '',
		suffix: '',
		start_offset: 0,
		end_offset: 9,
		note: null,
		created_at: '2026-10-21T08:00:00Z',
		...overrides
	};
}

function card(overrides: Partial<Props> = {}) {
	const onsavenote = vi.fn(async (_note: string | null) => true);
	const ondelete = vi.fn(async () => undefined);
	const { container } = render(HighlightCard, {
		highlight: highlight(),
		onsavenote,
		ondelete,
		...overrides
	} as Props);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		onsavenote,
		ondelete,
		quote: () => q('[data-test-highlight-quote]')?.textContent?.trim(),
		note: () => q('[data-test-highlight-note]')?.textContent?.trim(),
		orphan: () => q('[data-test-highlight-orphan]'),
		article: () => q<HTMLAnchorElement>('[data-test-highlight-article]'),
		edit: () => q<HTMLButtonElement>('[data-test-highlight-edit]'),
		reveal: () => q<HTMLButtonElement>('[data-test-highlight-reveal]'),
		remove: () => q<HTMLButtonElement>('[data-test-highlight-delete]')!,
		field: () => q<HTMLTextAreaElement>('[data-test-highlight-note-field]'),
		save: () => q<HTMLButtonElement>('[data-test-highlight-note-save]')!,
		cancel: () => q<HTMLButtonElement>('[data-test-highlight-note-cancel]')!
	};
}

beforeEach(() => setLocale('en'));
afterEach(cleanup);

describe('showing a highlight', () => {
	it('quotes the passage and shows the note', () => {
		const view = card({ highlight: highlight({ note: 'Worth keeping' }) });

		expect(view.quote()).toBe('le papier');
		expect(view.note()).toBe('Worth keeping');
	});

	it('offers to add a note when there is none, and to edit it when there is', () => {
		expect(card().edit()?.textContent).toContain('Add a note');
		cleanup();
		expect(card({ highlight: highlight({ note: 'x' }) }).edit()?.textContent).toContain(
			'Edit note'
		);
	});

	it('links back to the article only when asked to', () => {
		expect(card().article()).toBeNull();
		cleanup();

		const view = card({ showArticle: true });

		expect(view.article()?.getAttribute('href')).toBe('/articles/article-1');
		expect(view.article()?.textContent).toContain('Le papier et l encre');
	});

	it('says an orphaned passage is gone from the text while still showing its note', () => {
		const view = card({ orphaned: true, highlight: highlight({ note: 'Still here' }) });

		expect(view.orphan()?.textContent).toContain('no longer in the article text');
		expect(view.note()).toBe('Still here');
	});

	it('shows no orphan notice for a passage that is in the text', () => {
		expect(card().orphan()).toBeNull();
	});
});

describe('revealing', () => {
	it('has no button to show the passage when it cannot be reached', () => {
		expect(card().reveal()).toBeNull();
	});

	it('scrolls to the passage on request', async () => {
		const onreveal = vi.fn();
		const view = card({ onreveal });

		await fireEvent.click(view.reveal()!);

		expect(onreveal).toHaveBeenCalledOnce();
	});
});

describe('editing the note', () => {
	it('opens a labelled field holding the current note and focuses it', async () => {
		const view = card({ highlight: highlight({ note: 'Old' }) });

		await fireEvent.click(view.edit()!);

		await waitFor(() => expect(view.field()).not.toBeNull());
		expect(view.field()?.value).toBe('Old');
		expect(document.activeElement).toBe(view.field());
		expect(document.querySelector(`label[for="${view.field()?.id}"]`)).not.toBeNull();
	});

	it('saves the trimmed note and closes the field', async () => {
		const view = card();
		await fireEvent.click(view.edit()!);
		await fireEvent.input(view.field()!, { target: { value: '  A thought  ' } });

		await fireEvent.click(view.save());

		await waitFor(() => expect(view.field()).toBeNull());
		expect(view.onsavenote).toHaveBeenCalledWith('A thought');
	});

	it('saves an emptied note as no note at all', async () => {
		const view = card({ highlight: highlight({ note: 'Old' }) });
		await fireEvent.click(view.edit()!);
		await fireEvent.input(view.field()!, { target: { value: '   ' } });

		await fireEvent.click(view.save());

		await waitFor(() => expect(view.onsavenote).toHaveBeenCalledWith(null));
	});

	it('leaves the note alone on cancel', async () => {
		const view = card();
		await fireEvent.click(view.edit()!);

		await fireEvent.click(view.cancel());

		expect(view.field()).toBeNull();
		expect(view.onsavenote).not.toHaveBeenCalled();
	});

	it('keeps the field open when saving fails', async () => {
		const onsavenote = vi.fn(async (_note: string | null) => false);
		const view = card({ onsavenote });
		await fireEvent.click(view.edit()!);

		await fireEvent.click(view.save());

		await waitFor(() => expect(onsavenote).toHaveBeenCalled());
		expect(view.field()).not.toBeNull();
	});
});

describe('deleting', () => {
	it('asks the owner to delete the highlight', async () => {
		const view = card();

		await fireEvent.click(view.remove());

		await waitFor(() => expect(view.ondelete).toHaveBeenCalledOnce());
	});
});
