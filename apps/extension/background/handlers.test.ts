import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeExtension } from '$test-support/fake-extension';
import { stubFetch } from '$test-support/stub-fetch';
import { en } from '$technical/i18n/messages/en';
import { registerBackground, SAVE_LINK_MENU_ID, SAVE_PAGE_COMMAND } from './handlers';

const SIGNED_IN = {
	'lumia.instance_url': 'https://lumia.test',
	'lumia.access_token': 'access',
	'lumia.refresh_token': 'refresh'
};

async function settle() {
	await vi.advanceTimersByTimeAsync(0);
}

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
	vi.unstubAllGlobals();
});

describe('context menu', () => {
	it('offers to save a link once installed', () => {
		const fake = createFakeExtension();
		registerBackground(fake.extension);
		fake.fire.installed();
		expect(fake.menus).toEqual([
			{ id: SAVE_LINK_MENU_ID, title: en['menu.saveLink'], contexts: ['link'] }
		]);
	});

	it('saves the link that was clicked, not the page it sits on', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN });
		const { requests } = stubFetch([{ status: 201, body: { id: 'a', already_saved: false } }]);
		registerBackground(fake.extension);
		fake.fire.menuClicked({ menuItemId: SAVE_LINK_MENU_ID, linkUrl: 'https://blog.test/linked' });
		await settle();
		expect(requests[0].body).toEqual({ url: 'https://blog.test/linked' });
		expect(fake.badge.title).toBe(en['save.saved']);
	});

	it('ignores a menu entry that is not its own', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN });
		const { requests } = stubFetch([]);
		registerBackground(fake.extension);
		fake.fire.menuClicked({ menuItemId: 'other', linkUrl: 'https://blog.test/linked' });
		await settle();
		expect(requests).toEqual([]);
	});
});

describe('keyboard shortcut', () => {
	it('saves the active tab and shows the result on the badge', async () => {
		const fake = createFakeExtension({
			stored: SIGNED_IN,
			tabs: [{ id: 3, url: 'https://blog.test/current' }]
		});
		stubFetch([{ status: 201, body: { id: 'a', already_saved: true } }]);
		registerBackground(fake.extension);
		fake.fire.command(SAVE_PAGE_COMMAND);
		await settle();
		expect(fake.badge.title).toBe(en['save.alreadySaved']);
		expect(fake.optionsPageOpened()).toBe(0);
	});

	it('ignores another command', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN, tabs: [{ url: 'https://blog.test/' }] });
		const { requests } = stubFetch([]);
		registerBackground(fake.extension);
		fake.fire.command('something-else');
		await settle();
		expect(requests).toEqual([]);
	});

	it('opens the settings when nothing is configured yet', async () => {
		const fake = createFakeExtension({ tabs: [{ url: 'https://blog.test/current' }] });
		registerBackground(fake.extension);
		fake.fire.command(SAVE_PAGE_COMMAND);
		await settle();
		expect(fake.badge.title).toBe(en['save.unconfigured']);
		expect(fake.optionsPageOpened()).toBe(1);
	});

	it('shows a failure on the badge without opening the settings', async () => {
		const fake = createFakeExtension({
			stored: SIGNED_IN,
			tabs: [{ url: 'https://blog.test/current' }]
		});
		stubFetch([{ status: 400 }]);
		registerBackground(fake.extension);
		fake.fire.command(SAVE_PAGE_COMMAND);
		await settle();
		expect(fake.badge.title).toBe(en['save.failed']);
		expect(fake.optionsPageOpened()).toBe(0);
	});

	it('copes with no active tab', async () => {
		const fake = createFakeExtension({ stored: SIGNED_IN, tabs: [] });
		registerBackground(fake.extension);
		fake.fire.command(SAVE_PAGE_COMMAND);
		await settle();
		expect(fake.badge.title).toBe(en['save.unsupported']);
	});
});
