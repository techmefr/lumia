import type { Folder } from '@lumia/core';

/** `fallback` is passed in rather than translated here, so this stays a pure lookup. */
export function resolveFolderName(
	folders: Folder[],
	folderId: string | null,
	fallback: string
): string {
	if (!folderId) return fallback;
	return folders.find((folder) => folder.id === folderId)?.name ?? fallback;
}
