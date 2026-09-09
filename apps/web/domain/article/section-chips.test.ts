import type { Folder, UnreadCounts } from '@lumia/core';
import { fireEvent, render } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SectionChips from './section-chips.svelte';

type Props = Parameters<typeof SectionChips>[1];

const FOLDERS: Folder[] = [
	{ id: 'folder-news', name: 'Actualités' },
	{ id: 'folder-tech', name: 'Technique' }
];

const NO_UNREAD: UnreadCounts = { total: 0, folders: {}, feeds: {} };

function chips(overrides: Partial<Props> = {}) {
	const onSelectAll = vi.fn();
	const onSelectFolder = vi.fn();
	const { container } = render(SectionChips, {
		folders: FOLDERS,
		unread: NO_UNREAD,
		selectedFolderId: '',
		onSelectAll,
		onSelectFolder,
		...overrides
	} as Props);

	const chip = (id: string) =>
		container.querySelector<HTMLButtonElement>(`[data-test-section-chip="${id}"]`)!;

	return {
		container,
		onSelectAll,
		onSelectFolder,
		chip,
		all: () => chip(''),
		labels: () =>
			[...container.querySelectorAll('[data-test-section-chip]')].map((node) =>
				node.textContent?.trim().replace(/\s+/g, ' ')
			),
		countOf: (id: string) => chip(id).querySelector('[data-test-chip-count]')?.textContent
	};
}

describe('what it lists', () => {
	it('offers every folder, plus an entry for everything', () => {
		expect(chips().labels()).toHaveLength(3);
	});

	it('names each folder', () => {
		const labels = chips().labels();
		expect(labels[1]).toContain('Actualités');
		expect(labels[2]).toContain('Technique');
	});

	it('keeps the folders in the order it was handed them', () => {
		const view = chips({ folders: [...FOLDERS].reverse() });
		expect(view.labels()[1]).toContain('Technique');
	});

	it('offers only the everything entry when there are no folders', () => {
		expect(chips({ folders: [] }).labels()).toHaveLength(1);
	});
});

describe('what is selected', () => {
	// A row of chips is a set of toggles, not links: `aria-pressed` is what tells a screen reader
	// which section is being shown, and it is the only marker that is not purely visual.
	it('presses the everything chip when no folder is selected', () => {
		const view = chips();
		expect(view.all().getAttribute('aria-pressed')).toBe('true');
		expect(view.chip('folder-news').getAttribute('aria-pressed')).toBe('false');
	});

	it('presses the selected folder and nothing else', () => {
		const view = chips({ selectedFolderId: 'folder-tech' });
		expect(view.chip('folder-tech').getAttribute('aria-pressed')).toBe('true');
		expect(view.chip('folder-news').getAttribute('aria-pressed')).toBe('false');
		expect(view.all().getAttribute('aria-pressed')).toBe('false');
	});

	it('presses exactly one chip at a time', () => {
		const view = chips({ selectedFolderId: 'folder-news' });
		const pressed = [...view.container.querySelectorAll('[aria-pressed="true"]')];
		expect(pressed).toHaveLength(1);
	});

	// A folder that no longer exists — deleted in another tab — must not leave the row with nothing
	// selected *and* nothing to fall back to. The everything chip stays unpressed, which is honest:
	// the page is filtered by something not on show.
	it('presses nothing when the selection is a folder it does not have', () => {
		const view = chips({ selectedFolderId: 'folder-gone' });
		expect(view.container.querySelectorAll('[aria-pressed="true"]')).toHaveLength(0);
	});
});

describe('the unread counts', () => {
	it('shows the total on the everything chip', () => {
		expect(chips({ unread: { total: 12, folders: {}, feeds: {} } }).countOf('')).toBe('12');
	});

	it('shows each folder its own count', () => {
		const view = chips({
			unread: { total: 9, folders: { 'folder-news': 7, 'folder-tech': 2 }, feeds: {} }
		});
		expect(view.countOf('folder-news')).toBe('7');
		expect(view.countOf('folder-tech')).toBe('2');
	});

	// A zero is noise on every chip of a fully-read library: nothing to read is said by the absence
	// of a badge, not by a badge saying nothing.
	it('shows no badge for a folder with nothing unread', () => {
		const view = chips({ unread: { total: 7, folders: { 'folder-news': 7 }, feeds: {} } });
		expect(view.countOf('folder-tech')).toBeUndefined();
	});

	it('shows no badge on the everything chip when the library is read', () => {
		expect(chips().countOf('')).toBeUndefined();
	});

	it('treats a folder the counts do not mention as read', () => {
		const view = chips({ unread: { total: 3, folders: {}, feeds: {} } });
		expect(view.countOf('folder-news')).toBeUndefined();
	});
});

describe('choosing a section', () => {
	it('asks for everything when the everything chip is pressed', async () => {
		const view = chips({ selectedFolderId: 'folder-news' });

		await fireEvent.click(view.all());

		expect(view.onSelectAll).toHaveBeenCalledTimes(1);
		expect(view.onSelectFolder).not.toHaveBeenCalled();
	});

	it('asks for the folder that was pressed', async () => {
		const view = chips();

		await fireEvent.click(view.chip('folder-tech'));

		expect(view.onSelectFolder).toHaveBeenCalledWith('folder-tech');
	});

	it('asks again when the chip already selected is pressed', async () => {
		const view = chips({ selectedFolderId: 'folder-tech' });

		await fireEvent.click(view.chip('folder-tech'));

		expect(view.onSelectFolder).toHaveBeenCalledWith('folder-tech');
	});
});

describe('reaching the sections without a mouse', () => {
	// This row is the only way to the sections on a phone, where the sidebar is hidden. Real
	// buttons in a labelled group is what makes it navigable rather than a strip of divs.
	it('groups the chips under a name', () => {
		const group = chips().container.querySelector('[role="group"]')!;
		expect(group.getAttribute('aria-label')).toBeTruthy();
	});

	it('makes every chip a real button', () => {
		for (const chip of chips().container.querySelectorAll('[data-test-section-chip]')) {
			expect(chip.tagName).toBe('BUTTON');
			expect(chip.getAttribute('type')).toBe('button');
		}
	});

	// 36 css pixels is the smallest comfortable touch target, and this row is thumb-driven.
	it('keeps every chip big enough to hit with a thumb', () => {
		for (const chip of chips().container.querySelectorAll('[data-test-section-chip]')) {
			expect(chip.className).toContain('min-h-9');
		}
	});
});
