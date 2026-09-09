import { defineConfig } from 'vitest/config';

export default defineConfig({
	test: {
		// jsdom even though nothing here is a component: the token store is localStorage and the
		// sanitiser needs a real DOM to parse into — that is the thing under test, not a detail.
		environment: 'jsdom',
		include: ['{domain,technical}/**/*.test.ts'],
		coverage: {
			provider: 'v8',
			include: ['{domain,technical}/**/*.ts'],
			// Type-only modules carry no runtime to cover.
			exclude: ['**/types.ts', '**/*.test.ts', 'index.ts'],
			reporter: ['text', 'lcov'],
			thresholds: { lines: 80, functions: 80, statements: 80, branches: 80 }
		}
	}
});
