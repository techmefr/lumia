import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
// From vitest rather than vite: the same config carries the `test` block, which vite's own
// `defineConfig` does not type.
import { defineConfig } from 'vitest/config';

// Declared rather than pulled from @types/node: this config is the only file in the app that
// reads an environment variable at build time.
declare const process: { env: Record<string, string | undefined> };

const basePath = (process.env.BASE_PATH ?? '') as '' | `/${string}`;

// Under vitest, svelte would otherwise resolve to its server build and `mount` throws. Only for
// the test run: forcing it on the real build would drop the SSR entry points sveltekit needs.
const testResolve = process.env.VITEST ? { conditions: ['browser'] } : undefined;

export default defineConfig({
	plugins: [
		tailwindcss(),
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},

			// Static SPA build: apps/mobile wraps this same output via Capacitor,
			// so there is no Node/edge server target to adapt to.
			adapter: adapter({ fallback: 'index.html' }),

			// Empty by default (served at a domain root by nginx); the github pages demo is
			// published under a sub-path and sets BASE_PATH at build time.
			paths: { base: basePath },

			alias: {
				$technical: 'technical',
				'$technical/*': 'technical/*',
				$domain: 'domain',
				'$domain/*': 'domain/*'
			}
		})
	],

	resolve: testResolve,

	test: {
		// jsdom rather than node: almost everything here reads localStorage, document or navigator,
		// and stubbing those by hand is how a test ends up proving the stub works.
		environment: 'jsdom',
		setupFiles: ['./vitest-setup.ts'],
		// The demo client delays every call on purpose so the real app shows its skeletons, which a
		// test exercising a dozen of them in sequence pays for. Raised once here rather than
		// per-test, so no case is ever tempted to shorten its scenario to fit the default.
		testTimeout: 20_000,
		include: ['{domain,technical,src}/**/*.test.ts'],
		exclude: ['**/node_modules/**'],
		coverage: {
			provider: 'v8',
			// The design system has its own runner and its own number: v8 coverage does not reach
			// outside the project root anyway, so a component tested there was counted nowhere.
			include: ['{domain,technical}/**/*.{ts,svelte}', 'src/{lib,routes}/**/*.{ts,svelte}'],
			exclude: [
				// Ten dictionaries of literal strings. Importing one marks it fully covered and
				// inflates the total by a third without a single behaviour being exercised.
				'technical/i18n/messages/**',
				// The demo fixtures are data too, read by the demo client the tests do cover.
				'technical/api/demo/seed.ts',
				'**/*.test.ts',
				'**/index.ts'
			],
			reporter: ['text', 'lcov'],
			/**
			 * A ratchet, not the target. 80 is the target and the shared core already sits at 100,
			 * but this project also carries every screen and every route page — roughly 5700 lines
			 * of svelte with no test yet. Floored just under what the suite covers today so the
			 * number can only go up; raise it with each batch of component tests, never lower it to
			 * make a red run green.
			 */
			thresholds: { lines: 39, functions: 33, statements: 36, branches: 38 }
		}
	}
});
