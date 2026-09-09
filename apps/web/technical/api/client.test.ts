import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
	vi.unstubAllEnvs();
	vi.resetModules();
});

async function loadClient(demo: string | undefined) {
	if (demo === undefined) vi.stubEnv('VITE_DEMO', '');
	else vi.stubEnv('VITE_DEMO', demo);
	vi.resetModules();
	return import('./client');
}

describe('which client the app talks to', () => {
	// The demo is the real front end with the http client swapped for an in-memory one, which is
	// what lets it be published as a static page and tried on a phone with no backend at all.
	it('uses the in-memory client in a demo build', async () => {
		const { isDemo, lumia } = await loadClient('true');

		expect(isDemo).toBe(true);
		expect(lumia.article).toBeDefined();
		expect(lumia.user).toBeDefined();
	});

	it('uses the http client otherwise', async () => {
		const { isDemo, lumia } = await loadClient(undefined);

		expect(isDemo).toBe(false);
		expect(lumia.article).toBeDefined();
	});

	// Only the exact string counts: a build where the flag was left at its default must be the real
	// client, or a self-hosted install would silently serve seed articles.
	it.each(['false', '1', 'TRUE', 'yes'])('treats %p as not a demo', async (value) => {
		const { isDemo } = await loadClient(value);

		expect(isDemo).toBe(false);
	});

	it('exposes the same surface either way, so the app never branches on it', async () => {
		const demo = await loadClient('true');
		const real = await loadClient(undefined);

		expect(Object.keys(demo.lumia).sort()).toEqual(Object.keys(real.lumia).sort());
	});
});
