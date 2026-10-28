import { createLumiaClient, type LumiaClient } from '@lumia/core';
import type { StorageArea } from '$technical/browser/extension-api';
import { apiBaseUrl, readInstanceUrl } from '$technical/storage/instance-settings';
import { createExtensionTokenStore } from '$technical/storage/extension-token-store';

export async function openLumiaClient(area: StorageArea): Promise<LumiaClient | null> {
	const instanceUrl = await readInstanceUrl(area);
	if (instanceUrl === null) return null;
	const tokenStore = await createExtensionTokenStore(area);
	return createLumiaClient(apiBaseUrl(instanceUrl), tokenStore);
}
