import tailwindcss from '@tailwindcss/vite';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

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

			alias: {
				$technical: 'technical',
				'$technical/*': 'technical/*',
				$domain: 'domain',
				'$domain/*': 'domain/*'
			}
		})
	]
});
