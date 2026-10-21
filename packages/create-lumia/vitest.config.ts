import { defineConfig } from "vitest/config";

export default defineConfig({
	test: {
		environment: "node",
		include: ["src/**/*.test.ts"],
		coverage: {
			provider: "v8",
			include: ["src/**/*.ts"],
			exclude: [
				"src/**/*.test.ts",
				"src/index.ts",
				"src/adapters/**",
				"src/types.ts",
				"src/test-support/**"
			],
			reporter: ["text", "lcov"],
			thresholds: { lines: 80, functions: 80, statements: 80, branches: 80 }
		}
	}
});
