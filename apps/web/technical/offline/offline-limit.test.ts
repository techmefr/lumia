import { describe, expect, it, vi } from 'vitest';
import {
	DEFAULT_OFFLINE_LIMIT,
	OFFLINE_LIMIT_OPTIONS,
	getOfflineLimit,
	setOfflineLimit
} from './offline-limit';

describe('the offline limit', () => {
	it('defaults to a bounded amount, never the whole account', () => {
		expect(getOfflineLimit()).toBe(DEFAULT_OFFLINE_LIMIT);
		expect(OFFLINE_LIMIT_OPTIONS).toContain(DEFAULT_OFFLINE_LIMIT);
	});

	it('remembers a choice, zero included', () => {
		setOfflineLimit(100);
		expect(getOfflineLimit()).toBe(100);

		setOfflineLimit(0);
		expect(getOfflineLimit()).toBe(0);
	});

	it('ignores a stored value that is not one of the offered caps', () => {
		localStorage.setItem('lumia-offline-limit', '7');
		expect(getOfflineLimit()).toBe(DEFAULT_OFFLINE_LIMIT);

		localStorage.setItem('lumia-offline-limit', 'lots');
		expect(getOfflineLimit()).toBe(DEFAULT_OFFLINE_LIMIT);
	});

	it('still answers when storage is blocked', () => {
		vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
			throw new Error('blocked');
		});
		vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
			throw new Error('blocked');
		});

		expect(getOfflineLimit()).toBe(DEFAULT_OFFLINE_LIMIT);
		expect(() => setOfflineLimit(25)).not.toThrow();
		vi.restoreAllMocks();
	});
});
