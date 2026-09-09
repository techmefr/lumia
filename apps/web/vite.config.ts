import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Declared rather than pulled from @types/node: this config is the only file in the app that
// reads an environment variable at build time.
declare const process: { env: Record<string, string | undefined> };

const basePath = (process.env.BASE_PATH ?? '') as '' | `/${string}`;

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

	test: {
		// jsdom rather than node: almost everything here reads localStorage, document or navigator,
		// and stubbing those by hand is how a test ends up proving the stub works.
		environment: 'jsdom',
		setupFiles: ['./vitest-setup.ts'],
		// The demo client delays every call on purpose so the real app shows its skeletons, which a
		// test exercising a dozen of them in sequence pays for. Raised once here rather than
		// per-test, so no case is ever tempted to shorten its scenario to fit the default.
		testTimeout: 20_000,
		// The design system is a sibling package with no runner of its own; its components only ever
		// render inside this app, so they are tested by the app that compiles them.
		include: ['{domain,technical,src}/**/*.test.ts', '../../packages/ui/**/*.test.ts'],
		coverage: {
			provider: 'v8',
			include: [
				'{domain,technical}/**/*.{ts,svelte}',
				'src/{lib,routes}/**/*.{ts,svelte}',
				'../../packages/ui/**/*.{ts,svelte}'
			],
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
			thresholds: { lines: 80, functions: 80, statements: 80, branches: 80 }
		}
	}
});
