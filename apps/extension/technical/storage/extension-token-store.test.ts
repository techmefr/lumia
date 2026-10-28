import { describe, expect, it } from 'vitest';
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
