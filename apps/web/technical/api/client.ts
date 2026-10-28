import { createLumiaClient, type LumiaClient } from '@lumia/core';
import { createDemoClient } from './demo/demo-client';
import { resolveApiBaseUrl } from '$technical/instance/instance-url';
import { isNativePlatform } from '$technical/platform/native-platform';

/**
 * The demo build swaps the http client for an in-memory one seeded with articles, so the app
 * can be published as a static page and tried on any device without a backend.
 */
export const isDemo = import.meta.env.VITE_DEMO === 'true';

export const apiBaseUrl: string = isNativePlatform()
	? resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL, localStorage)
	: import.meta.env.VITE_API_BASE_URL;

export const lumia: LumiaClient = isDemo ? createDemoClient() : createLumiaClient(apiBaseUrl);
