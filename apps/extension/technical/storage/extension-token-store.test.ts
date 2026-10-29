import { describe, expect, it, vi } from 'vitest';
import { createFakeExtension } from '$test-support/fake-extension';
import { createExtensionTokenStore } from './extension-token-store';

describe('createExtensionTokenStore', () => {
	it('starts empty when nothing was stored', async () => {
		const { extension } = createFakeExtension();
		const store = await createExtensionTokenStore(extension.storage.local);
		expect(store.getAccessToken()).toBeNull();
		expect(store.getRefreshToken()).toBeNull();
	});

	it('reads back the tokens a previous session left in the extension storage', async () => {
		const { extension } = createFakeExtension({
			stored: { 'lumia.access_token': 'a', 'lumia.refresh_token': 'r' }
		});
		const store = await createExtensionTokenStore(extension.storage.local);
		expect(store.getAccessToken()).toBe('a');
		expect(store.getRefreshToken()).toBe('r');
	});

	it('ignores a stored value that is not a string', async () => {
		const { extension } = createFakeExtension({ stored: { 'lumia.access_token': 42 } });
		const store = await createExtensionTokenStore(extension.storage.local);
		expect(store.getAccessToken()).toBeNull();
	});

	it('persists both tokens so another extension page finds them', async () => {
		const { extension, store: persisted } = createFakeExtension();
		const store = await createExtensionTokenStore(extension.storage.local);
		store.setTokens({ accessToken: 'a2', refreshToken: 'r2' });
		expect(persisted).toEqual({ 'lumia.access_token': 'a2', 'lumia.refresh_token': 'r2' });
		const reopened = await createExtensionTokenStore(extension.storage.local);
		expect(reopened.getRefreshToken()).toBe('r2');
	});

	it('replaces the access token alone', async () => {
		const { extension, store: persisted } = createFakeExtension({
			stored: { 'lumia.access_token': 'a', 'lumia.refresh_token': 'r' }
		});
		const store = await createExtensionTokenStore(extension.storage.local);
		store.setAccessToken('a3');
		expect(store.getAccessToken()).toBe('a3');
		expect(persisted).toEqual({ 'lumia.access_token': 'a3', 'lumia.refresh_token': 'r' });
	});

	it('forgets both tokens on clear, in memory and in storage', async () => {
		const { extension, store: persisted } = createFakeExtension({
			stored: { 'lumia.access_token': 'a', 'lumia.refresh_token': 'r' }
		});
		const store = await createExtensionTokenStore(extension.storage.local);
		store.clear();
		expect(store.getAccessToken()).toBeNull();
		expect(store.getRefreshToken()).toBeNull();
		expect(persisted).toEqual({});
	});
});

describe('createExtensionTokenStore writes', () => {
	function slowArea() {
		const { extension, store: persisted } = createFakeExtension();
		const area = extension.storage.local;
		const order: string[] = [];
		return {
			persisted,
			order,
			area: {
				get: area.get,
				set: async (items: Record<string, unknown>) => {
					await new Promise((resolve) => setTimeout(resolve, 5));
					order.push('set');
					await area.set(items);
				},
				remove: async (keys: string[]) => {
					order.push('remove');
					await area.remove(keys);
				}
			}
		};
	}

	it('exposes a promise that resolves once the storage holds the tokens', async () => {
		const { area, persisted } = slowArea();
		const store = await createExtensionTokenStore(area);
		store.setTokens({ accessToken: 'a', refreshToken: 'r' });
		expect(persisted).toEqual({});

		await store.settled?.();

		expect(persisted).toEqual({ 'lumia.access_token': 'a', 'lumia.refresh_token': 'r' });
	});

	it('applies writes in order, so a clear right after a login wins', async () => {
		const { area, persisted, order } = slowArea();
		const store = await createExtensionTokenStore(area);
		store.setTokens({ accessToken: 'a', refreshToken: 'r' });
		store.clear();

		await store.settled?.();

		expect(order).toEqual(['set', 'remove']);
		expect(persisted).toEqual({});
	});

	it('survives a failing write and keeps the later ones going', async () => {
		const { extension, store: persisted } = createFakeExtension();
		let failNext = true;
		const area = {
			get: extension.storage.local.get,
			remove: extension.storage.local.remove,
			set: async (items: Record<string, unknown>) => {
				if (failNext) {
					failNext = false;
					throw new Error('quota');
				}
				await extension.storage.local.set(items);
			}
		};
		const store = await createExtensionTokenStore(area);
		store.setAccessToken('lost');
		store.setAccessToken('kept');

		await store.settled?.();

		expect(persisted['lumia.access_token']).toBe('kept');
	});
});

describe('createExtensionTokenStore shared storage', () => {
	it('re-reads the storage on reload, which is the source of truth', async () => {
		const { extension, store: persisted } = createFakeExtension();
		const store = await createExtensionTokenStore(extension.storage.local);
		persisted['lumia.access_token'] = 'from-other-page';
		persisted['lumia.refresh_token'] = 'rotated';

		await store.reload?.();

		expect(store.getAccessToken()).toBe('from-other-page');
		expect(store.getRefreshToken()).toBe('rotated');
	});

	it('follows storage changes made by another page', async () => {
		const { extension } = createFakeExtension();
		let notify: (changes: Record<string, { newValue?: unknown }>) => void = () => undefined;
		const area = {
			...extension.storage.local,
			onChanged: { addListener: (listener: typeof notify) => (notify = listener) }
		};
		const store = await createExtensionTokenStore(area);

		notify({ 'lumia.refresh_token': { newValue: 'r9' }, 'lumia.access_token': { newValue: 'a9' } });
		expect(store.getRefreshToken()).toBe('r9');
		expect(store.getAccessToken()).toBe('a9');

		notify({ 'lumia.access_token': {}, 'lumia.refresh_token': {} });
		expect(store.getAccessToken()).toBeNull();
	});

	it('serialises refreshes through the web lock when the browser has one', async () => {
		const request = vi.fn(async (_name: string, task: () => Promise<unknown>) => task());
		vi.stubGlobal('navigator', { locks: { request } });
		const { extension } = createFakeExtension();
		const store = await createExtensionTokenStore(extension.storage.local);

		await expect(store.exclusive?.(async () => 7)).resolves.toBe(7);
		vi.unstubAllGlobals();

		expect(request).toHaveBeenCalledWith('lumia-token-refresh', expect.any(Function));
	});

	it('just runs the task when there is no lock api', async () => {
		const { extension } = createFakeExtension();
		const store = await createExtensionTokenStore(extension.storage.local);
		await expect(store.exclusive?.(async () => 3)).resolves.toBe(3);
	});
});
