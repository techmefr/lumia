import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [svelte({ compilerOptions: { runes: true } })],

	// Without it svelte resolves to its server build and `mount` throws.
	resolve: { conditions: ['browser'] },

	test: {
		environment: 'jsdom',
		setupFiles: ['./vitest-setup.ts'],
		include: ['{domain,technical}/**/*.test.ts'],
		exclude: ['**/node_modules/**'],
		coverage: {
			provider: 'v8',
			include: ['{domain,technical}/**/*.{ts,svelte}'],
			exclude: ['**/*.test.ts', 'index.ts'],
			reporter: ['text', 'lcov'],
			/**
			 * A ratchet, set just under what the suite covers today. Every component and effect in
			 * the package is now tested; what the branch figure is missing is the handful of prop
			 * defaults no caller in the app overrides. Raise it when you add tests, never lower it
			 * to turn a red run green.
			 */
			thresholds: { lines: 99, functions: 99, statements: 98, branches: 85 }
		}
	}
});
