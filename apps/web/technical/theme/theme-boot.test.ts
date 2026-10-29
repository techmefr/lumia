import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { beforeEach, describe, expect, it } from 'vitest';

const html = readFileSync(resolve(process.cwd(), 'src/app.html'), 'utf8');
const script = readFileSync(resolve(process.cwd(), 'static/theme-boot.js'), 'utf8');
const root = () => document.documentElement;
const metas = () => [...document.querySelectorAll('meta[name="theme-color"]')];

function boot(stored: Record<string, string>, systemDark = false) {
	localStorage.clear();
	for (const [key, value] of Object.entries(stored)) localStorage.setItem(key, value);
	window.matchMedia = ((query: string) => ({
		matches: systemDark && query.includes('dark'),
		media: query
	})) as typeof window.matchMedia;
	new Function(script)();
}

beforeEach(() => {
	root().className = '';
	root().removeAttribute('style');
	root().removeAttribute('data-theme');
	document.head.innerHTML = `
		<meta name="theme-color" content="#0b0b0f" media="(prefers-color-scheme: dark)" />
		<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)" />`;
});

describe('the early theme script', () => {
	it('is loaded synchronously from a file, because the CSP blocks inline scripts', () => {
		expect(html).toContain('<script src="%sveltekit.assets%/theme-boot.js"></script>');
		expect(html).not.toMatch(/<script(?![^>]*\ssrc=)[^>]*>/);
	});

	it('paints a dark named theme with the dark class and its data-theme', () => {
		boot({ 'lumia-theme': 'dracula' });
		expect(root().dataset.theme).toBe('dracula');
		expect(root().classList.contains('dark')).toBe(true);
	});

	it('paints a light named theme without the dark class', () => {
		boot({ 'lumia-theme': 'alucard' }, true);
		expect(root().dataset.theme).toBe('alucard');
		expect(root().classList.contains('dark')).toBe(false);
	});

	it('leaves the accent to the palette of a named theme', () => {
		boot({ 'lumia-theme': 'nord', 'lumia-accent': 'vert' });
		expect(root().style.getPropertyValue('--primary')).toBe('');
		expect(root().style.getPropertyValue('--ring')).toBe('');
	});

	it('updates every theme-color meta to the palette background', () => {
		boot({ 'lumia-theme': 'solarized-light' });
		expect(metas().map((meta) => meta.getAttribute('content'))).toEqual(['#fdf6e3', '#fdf6e3']);
		expect(metas().every((meta) => !meta.hasAttribute('media'))).toBe(true);
	});

	it('keeps the accent for the plain dark theme', () => {
		boot({ 'lumia-theme': 'dark', 'lumia-accent': 'vert' });
		expect(root().classList.contains('dark')).toBe(true);
		expect(root().dataset.theme).toBeUndefined();
		expect(root().style.getPropertyValue('--primary')).toContain('145');
	});

	it('follows the system when nothing is stored', () => {
		boot({}, true);
		expect(root().classList.contains('dark')).toBe(true);
		expect(metas().every((meta) => meta.hasAttribute('media'))).toBe(true);
	});

	it('falls back to the former behaviour on an unknown stored theme', () => {
		boot({ 'lumia-theme': 'vaporwave' }, true);
		expect(root().dataset.theme).toBeUndefined();
		expect(root().classList.contains('dark')).toBe(false);
		expect(root().style.getPropertyValue('--primary')).not.toBe('');
	});

	it('does not read inherited object keys as themes', () => {
		boot({ 'lumia-theme': 'constructor' });
		expect(root().dataset.theme).toBeUndefined();
	});
});
