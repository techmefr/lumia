import { ApiError, type Tag } from '@lumia/core';
import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import TagManager from './tag-manager.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { tag: { listTags: vi.fn(), renameTag: vi.fn(), deleteTag: vi.fn() } }
}));

const api = vi.mocked(lumia.tag);

const TAGS: Tag[] = [
	{ id: 't1', name: 'Cuisine', article_count: 3 },
	{ id: 't2', name: 'Voyage', article_count: 0 }
];

function panel() {
	const { container } = render(TagManager);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		rows: () =>
			[...container.querySelectorAll<HTMLElement>('[data-test-tag-row]')].map((row) => ({
				id: row.dataset.testTagRow,
				name: row.querySelector('[data-test-tag-name]')?.textContent?.trim(),
				count: row.querySelector('[data-test-tag-count]')?.textContent?.trim()
			})),
		row: (id: string) => q<HTMLElement>(`[data-test-tag-row="${id}"]`)!,
		empty: () => q('[data-test-tags-empty]'),
		error: () => q('[data-test-tags-error]')
	};
}

async function loaded() {
	const view = panel();
	await vi.waitFor(() => expect(api.listTags).toHaveBeenCalled());
	return view;
}

beforeEach(() => {
	api.listTags.mockResolvedValue(TAGS);
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.resetAllMocks();
	vi.unstubAllGlobals();
});

describe('the list', () => {
	it('shows each tag with the number of articles it carries', async () => {
		const view = await loaded();
		await vi.waitFor(() =>
			expect(view.rows()).toEqual([
				{ id: 't1', name: 'Cuisine', count: 'Articles: 3' },
				{ id: 't2', name: 'Voyage', count: 'Articles: 0' }
			])
		);
	});

	it('says there is none rather than showing an empty box', async () => {
		api.listTags.mockResolvedValue([]);
		const view = await loaded();
		await vi.waitFor(() => expect(view.empty()).not.toBeNull());
	});

	it('reports a failed load', async () => {
		api.listTags.mockRejectedValue(new Error('down'));
		const view = await loaded();
		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.empty()).toBeNull();
	});
});

describe('renaming', () => {
	async function openRename(view: ReturnType<typeof panel>, id: string) {
		await vi.waitFor(() => expect(view.rows()).toHaveLength(2));
		await fireEvent.click(view.row(id).querySelector('[data-test-tag-rename]')!);
	}

	it('saves the new name and updates the row', async () => {
		api.renameTag.mockResolvedValue({ id: 't1', name: 'Recettes', article_count: 3 });
		const view = await loaded();
		await openRename(view, 't1');
		const input = view.row('t1').querySelector<HTMLInputElement>('[data-test-tag-rename-input]')!;
		expect(input.value).toBe('Cuisine');
		await fireEvent.input(input, { target: { value: ' Recettes ' } });
		await fireEvent.submit(view.row('t1').querySelector('form')!);
		await vi.waitFor(() => expect(view.rows()[0].name).toBe('Recettes'));
		expect(api.renameTag).toHaveBeenCalledWith('t1', 'Recettes');
	});

	it('explains a name clash instead of failing silently', async () => {
		api.renameTag.mockRejectedValue(new ApiError(409, { detail: 'tag_name_taken' }));
		const view = await loaded();
		await openRename(view, 't1');
		await fireEvent.submit(view.row('t1').querySelector('form')!);
		await vi.waitFor(() => expect(view.error()?.textContent).toContain('already exists'));
	});

	it('reports any other failure as a failure to save', async () => {
		api.renameTag.mockRejectedValue(new Error('down'));
		const view = await loaded();
		await openRename(view, 't1');
		await fireEvent.submit(view.row('t1').querySelector('form')!);
		await vi.waitFor(() => expect(view.error()?.textContent).toContain('could not be saved'));
	});

	it('leaves the tag alone when cancelled', async () => {
		const view = await loaded();
		await openRename(view, 't1');
		await fireEvent.click(view.row('t1').querySelector('[data-test-tag-rename-cancel]')!);
		expect(view.rows()[0].name).toBe('Cuisine');
		expect(api.renameTag).not.toHaveBeenCalled();
	});
});

describe('deleting', () => {
	it('asks first, naming the tag and how many articles lose it', async () => {
		const confirmation = vi.fn(() => false);
		vi.stubGlobal('confirm', confirmation);
		const view = await loaded();
		await vi.waitFor(() => expect(view.rows()).toHaveLength(2));
		await fireEvent.click(view.row('t1').querySelector('[data-test-tag-delete]')!);
		expect(confirmation).toHaveBeenCalledWith(expect.stringContaining('Cuisine'));
		expect(confirmation).toHaveBeenCalledWith(expect.stringContaining('3'));
		expect(api.deleteTag).not.toHaveBeenCalled();
	});

	it('removes the row once confirmed', async () => {
		vi.stubGlobal('confirm', () => true);
		api.deleteTag.mockResolvedValue(undefined);
		const view = await loaded();
		await vi.waitFor(() => expect(view.rows()).toHaveLength(2));
		await fireEvent.click(view.row('t1').querySelector('[data-test-tag-delete]')!);
		await vi.waitFor(() => expect(view.rows().map((row) => row.id)).toEqual(['t2']));
		expect(api.deleteTag).toHaveBeenCalledWith('t1');
	});

	it('keeps the row and says so when the delete fails', async () => {
		vi.stubGlobal('confirm', () => true);
		api.deleteTag.mockRejectedValue(new Error('down'));
		const view = await loaded();
		await vi.waitFor(() => expect(view.rows()).toHaveLength(2));
		await fireEvent.click(view.row('t1').querySelector('[data-test-tag-delete]')!);
		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(view.rows()).toHaveLength(2);
	});
});
