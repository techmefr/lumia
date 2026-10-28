import { describe, expect, it } from 'vitest';
import { createFakeExtension } from '$test-support/fake-extension';
import {
	apiBaseUrl,
	hostPermissionPattern,
	normalizeInstanceUrl,
	readInstanceUrl,
	writeInstanceUrl
} from './instance-settings';

describe('normalizeInstanceUrl', () => {
	it.each([
		['https://lumia.example.com', 'https://lumia.example.com'],
		['  https://lumia.example.com/  ', 'https://lumia.example.com'],
		['http://localhost:8080', 'http://localhost:8080'],
		['https://example.com/lumia//', 'https://example.com/lumia']
	])('accepts %s', (input, expected) => {
		expect(normalizeInstanceUrl(input)).toBe(expected);
	});

	it.each(['', '   ', 'lumia.example.com', 'ftp://example.com', 'javascript:alert(1)'])(
		'rejects %j',
		(input) => {
			expect(normalizeInstanceUrl(input)).toBeNull();
		}
	);

	it('drops the query and fragment, which are never part of an instance address', () => {
		expect(normalizeInstanceUrl('https://example.com/?a=1#top')).toBe('https://example.com');
	});
});

describe('derived addresses', () => {
	it('puts the api under /api of the instance, as the shipped nginx does', () => {
		expect(apiBaseUrl('https://example.com')).toBe('https://example.com/api');
	});

	it('asks for the whole origin, whatever sub-path the instance lives under', () => {
		expect(hostPermissionPattern('https://example.com/lumia')).toBe('https://example.com/*');
	});
});

describe('instance address storage', () => {
	it('is empty until one is written', async () => {
		const { extension } = createFakeExtension();
		expect(await readInstanceUrl(extension.storage.local)).toBeNull();
	});

	it('hands back what was written', async () => {
		const { extension } = createFakeExtension();
		await writeInstanceUrl(extension.storage.local, 'https://example.com');
		expect(await readInstanceUrl(extension.storage.local)).toBe('https://example.com');
	});

	it('treats a blank stored value as no address', async () => {
		const { extension } = createFakeExtension({ stored: { 'lumia.instance_url': '' } });
		expect(await readInstanceUrl(extension.storage.local)).toBeNull();
	});
});
