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
	]
});
