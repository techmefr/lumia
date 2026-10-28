import { describe, expect, it } from 'vitest';
import { buildManifest } from './manifest';

describe('buildManifest', () => {
	it('is manifest v3 for both browsers', () => {
		expect(buildManifest('chrome', '1.2.3').manifest_version).toBe(3);
		expect(buildManifest('firefox', '1.2.3').manifest_version).toBe(3);
	});

	it('carries the package version', () => {
		expect(buildManifest('chrome', '1.2.3').version).toBe('1.2.3');
	});

	it('runs the background as a service worker on chrome and as a script on firefox', () => {
		expect(buildManifest('chrome', '1').background).toEqual({
			service_worker: 'background.js',
			type: 'module'
		});
		expect(buildManifest('firefox', '1').background).toEqual({
			scripts: ['background.js'],
			type: 'module'
		});
	});

	it('only names the firefox add-on id on firefox', () => {
		expect('browser_specific_settings' in buildManifest('chrome', '1')).toBe(false);
		expect('browser_specific_settings' in buildManifest('firefox', '1')).toBe(true);
	});

	it('asks up front for no host access: the instance is not known until the reader types it', () => {
		const manifest = buildManifest('chrome', '1');
		expect(manifest.permissions).not.toContain('<all_urls>');
		expect(manifest.optional_host_permissions).toEqual(['http://*/*', 'https://*/*']);
	});

	it('binds a keyboard shortcut to the save command', () => {
		const { commands } = buildManifest('chrome', '1');
		expect(commands['save-page'].suggested_key.default).toBe('Alt+Shift+L');
	});

	it('points at the popup and the settings page the build emits', () => {
		const manifest = buildManifest('chrome', '1');
		expect(manifest.action.default_popup).toBe('popup/index.html');
		expect(manifest.options_ui.page).toBe('options/index.html');
	});

	it('declares the reader panel the way each browser expects it', () => {
		const chrome = buildManifest('chrome', '1');
		const firefox = buildManifest('firefox', '1');
		expect(chrome.side_panel).toEqual({ default_path: 'sidepanel/index.html' });
		expect(chrome.permissions).toContain('sidePanel');
		expect('sidebar_action' in chrome).toBe(false);
		expect(firefox.sidebar_action).toMatchObject({ default_panel: 'sidepanel/index.html' });
		expect(firefox.permissions).not.toContain('sidePanel');
		expect('side_panel' in firefox).toBe(false);
	});

	it('binds a keyboard shortcut to the reader', () => {
		const { commands } = buildManifest('chrome', '1');
		expect(commands['open-reader'].suggested_key.default).toBe('Alt+Shift+K');
	});
});
