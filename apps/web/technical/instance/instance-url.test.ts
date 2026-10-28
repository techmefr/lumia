import { describe, expect, it } from 'vitest';
import {
	getStoredInstanceUrl,
	normalizeInstanceUrl,
	resolveApiBaseUrl,
	storeInstanceUrl
} from './instance-url';

function memoryStorage(initial: Record<string, string> = {}) {
	const data = new Map(Object.entries(initial));
	return {
		getItem: (key: string) => data.get(key) ?? null,
		setItem: (key: string, value: string) => void data.set(key, value)
	};
}

describe('normalizeInstanceUrl', () => {
	it('keeps the origin and path and drops trailing slashes', () => {
		expect(normalizeInstanceUrl('  https://lumia.example.com/api/// ')).toBe(
			'https://lumia.example.com/api'
		);
	});

	it('accepts a bare origin', () => {
		expect(normalizeInstanceUrl('http://192.168.1.10:8000')).toBe('http://192.168.1.10:8000');
	});

	it('drops the query string and fragment', () => {
		expect(normalizeInstanceUrl('https://a.example/api?x=1#top')).toBe('https://a.example/api');
	});

	it.each(['', '   ', 'lumia.example.com', 'ftp://lumia.example.com', 'javascript:alert(1)'])(
		'rejects %j',
		(raw) => {
			expect(normalizeInstanceUrl(raw)).toBeNull();
		}
	);
});

describe('resolveApiBaseUrl', () => {
	it('prefers the address the reader stored over the build-time one', () => {
		const storage = memoryStorage();
		storeInstanceUrl(storage, 'https://mine.example/api');
		expect(resolveApiBaseUrl('/api', storage)).toBe('https://mine.example/api');
	});

	it('falls back to the build-time address when nothing is stored', () => {
		expect(resolveApiBaseUrl('/api', memoryStorage())).toBe('/api');
	});

	it('falls back to an empty base when neither exists', () => {
		expect(resolveApiBaseUrl(undefined, undefined)).toBe('');
	});

	it('survives a storage that throws', () => {
		const broken = {
			getItem: () => {
				throw new Error('denied');
			},
			setItem: () => {
				throw new Error('denied');
			}
		};
		expect(getStoredInstanceUrl(broken)).toBeNull();
		expect(() => storeInstanceUrl(broken, 'https://a.example')).not.toThrow();
		expect(resolveApiBaseUrl('/api', broken)).toBe('/api');
	});
});
