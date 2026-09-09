import { describe, expect, it } from 'vitest';
import type { Folder } from '@lumia/core';
import { resolveFolderName } from './resolve-folder-name';

const FOLDERS = [
	{ id: 'folder-tech', name: 'Tech' },
	{ id: 'folder-design', name: 'Design' }
] as Folder[];

describe('resolveFolderName', () => {
	it('returns the name of the folder asked for', () => {
		expect(resolveFolderName(FOLDERS, 'folder-design', 'All articles')).toBe('Design');
	});

	it('falls back when no folder is selected', () => {
		expect(resolveFolderName(FOLDERS, null, 'All articles')).toBe('All articles');
	});

	it('falls back when the folder was deleted while the id was still in the url', () => {
		expect(resolveFolderName(FOLDERS, 'folder-gone', 'All articles')).toBe('All articles');
	});

	it('falls back on an empty id rather than matching a folder with an empty name', () => {
		expect(resolveFolderName(FOLDERS, '', 'All articles')).toBe('All articles');
	});

	it('falls back when there are no folders at all', () => {
		expect(resolveFolderName([], 'folder-tech', 'All articles')).toBe('All articles');
	});

	it('returns the first match when two folders share an id', () => {
		const duplicated = [...FOLDERS, { id: 'folder-tech', name: 'Tech bis' }] as Folder[];
		expect(resolveFolderName(duplicated, 'folder-tech', 'All articles')).toBe('Tech');
	});
});
