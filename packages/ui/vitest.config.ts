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
			 * A ratchet, not the target. One component of fifteen is covered so far; 80 is where
			 * this is going. Raise it with each component tested, never lower it to turn a red run
			 * green.
			 */
			thresholds: { lines: 20, functions: 16, statements: 22, branches: 30 }
		}
	}
});
