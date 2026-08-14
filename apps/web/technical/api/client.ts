import { createLumiaClient, type LumiaClient } from '@lumia/core';
import { createDemoClient } from './demo/demo-client';

/**
 * The demo build swaps the http client for an in-memory one seeded with articles, so the app
 * can be published as a static page and tried on any device without a backend.
 */
export const isDemo = import.meta.env.VITE_DEMO === 'true';

export const lumia: LumiaClient = isDemo
	? createDemoClient()
	: createLumiaClient(import.meta.env.VITE_API_BASE_URL);
