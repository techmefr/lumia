import type { StorageArea } from '$technical/browser/extension-api';

const INSTANCE_KEY = 'lumia.instance_url';

export function normalizeInstanceUrl(input: string): string | null {
	const trimmed = input.trim();
	if (trimmed === '') return null;
	let url: URL;
	try {
		url = new URL(trimmed);
	} catch {
		return null;
	}
	if (url.protocol !== 'https:' && url.protocol !== 'http:') return null;
	return `${url.origin}${url.pathname.replace(/\/+$/, '')}`;
}

export function apiBaseUrl(instanceUrl: string): string {
	return `${instanceUrl}/api`;
}

export function hostPermissionPattern(instanceUrl: string): string {
	return `${new URL(instanceUrl).origin}/*`;
}

export async function readInstanceUrl(area: StorageArea): Promise<string | null> {
	const stored = await area.get([INSTANCE_KEY]);
	const value = stored[INSTANCE_KEY];
	return typeof value === 'string' && value !== '' ? value : null;
}

export async function writeInstanceUrl(
	area: StorageArea,
	instanceUrl: string
): Promise<string | null> {
	const previous = await readInstanceUrl(area);
	const moved = previous !== null && new URL(previous).origin !== new URL(instanceUrl).origin;
	if (moved) await area.remove(['lumia.access_token', 'lumia.refresh_token']);
	await area.set({ [INSTANCE_KEY]: instanceUrl });
	return moved ? previous : null;
}
