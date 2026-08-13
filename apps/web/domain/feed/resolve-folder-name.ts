import type { Folder } from '@lumia/core';

export function resolveFolderName(folders: Folder[], folderId: string | null): string {
	if (!folderId) return 'Sans dossier';
	return folders.find((folder) => folder.id === folderId)?.name ?? 'Sans dossier';
}
