import { fileURLToPath } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { defineConfig } from 'vitest/config';
import { buildManifest, type ExtensionTarget } from './manifest.ts';
import pkg from './package.json' with { type: 'json' };

declare const process: { env: Record<string, string | undefined> };

const target: ExtensionTarget = process.env.EXTENSION_TARGET === 'firefox' ? 'firefox' : 'chrome';

const resolvePath = (relative: string) => fileURLToPath(new URL(relative, import.meta.url));

export default defineConfig({
	base: './',
	plugins: [
		tailwindcss(),
		svelte({ compilerOptions: { runes: true } }),
		{
			name: 'extension-manifest',
			generateBundle() {
				this.emitFile({
					type: 'asset',
					fileName: 'manifest.json',
					source: JSON.stringify(buildManifest(target, pkg.version), null, '\t')
				});
			}
		}
	],

	resolve: {
		conditions: ['browser'],
		alias: {
			$technical: resolvePath('./technical'),
			$domain: resolvePath('./domain'),
			'$test-support': resolvePath('./test-support')
		}
	},

	build: {
		outDir: `dist/${target}`,
		emptyOutDir: true,
		target: 'es2022',
		rollupOptions: {
			input: {
				popup: resolvePath('./popup/index.html'),
				options: resolvePath('./options/index.html'),
				background: resolvePath('./background/background.ts')
			},
			output: {
				entryFileNames: (chunk) =>
					chunk.name === 'background' ? 'background.js' : 'assets/[name]-[hash].js'
			}
		}
	},

	test: {
		environment: 'jsdom',
		setupFiles: ['./vitest-setup.ts'],
		include: ['{domain,technical,popup,options,background}/**/*.test.ts', 'manifest.test.ts'],
		exclude: ['**/node_modules/**'],
		coverage: {
			provider: 'v8',
			include: ['{domain,technical,popup,options,background}/**/*.{ts,svelte}', 'manifest.ts'],
			exclude: ['**/*.test.ts', 'technical/i18n/messages/**', '**/main.ts'],
			reporter: ['text', 'lcov'],
			thresholds: { lines: 80, functions: 80, statements: 80, branches: 80 }
		}
	}
});
