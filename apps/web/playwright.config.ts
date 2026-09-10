import { defineConfig, devices } from '@playwright/test';

// Declared rather than pulled from @types/node: like vite.config.ts, this file is one of the two
// places in the app allowed to read the environment.
declare const process: { env: Record<string, string | undefined> };

const PORT = 4173;
const isCI = Boolean(process.env.CI);

export default defineConfig({
	testDir: './e2e',
	// A journey drives the real demo client, whose calls are delayed on purpose.
	timeout: 60_000,
	expect: { timeout: 10_000 },
	fullyParallel: true,
	forbidOnly: isCI,
	// No retry: a journey that only passes on the second run is a journey nobody can trust.
	retries: 0,
	workers: isCI ? 2 : undefined,
	reporter: isCI ? [['list'], ['html', { open: 'never' }]] : [['list']],

	use: {
		baseURL: `http://127.0.0.1:${PORT}`,
		trace: 'retain-on-failure',
		screenshot: 'only-on-failure'
	},

	projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],

	// The demo build is the whole point of running against it: a static SPA seeded in memory, so a
	// journey needs no backend, no database and no fixture reset between tests.
	webServer: {
		command: `pnpm run build && pnpm run preview --port ${PORT} --strictPort`,
		url: `http://127.0.0.1:${PORT}/articles`,
		env: { VITE_DEMO: 'true', BASE_PATH: '' },
		reuseExistingServer: !isCI,
		timeout: 240_000
	}
});
