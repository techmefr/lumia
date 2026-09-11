import { describe, expect, it } from 'vitest';
import { formatDateInUserTimezone } from './format-date';

describe('formatDateInUserTimezone', () => {
	it('formats an ISO instant as a short date in the given locale', () => {
		const formatted = formatDateInUserTimezone('2026-08-12T10:00:00Z', 'en');
		expect(formatted).toMatch(/2026/);
		expect(formatted).toMatch(/Aug/);
	});

	it('renders the same instant differently depending on the locale', () => {
		const french = formatDateInUserTimezone('2026-01-05T10:00:00Z', 'fr');
		const english = formatDateInUserTimezone('2026-01-05T10:00:00Z', 'en');
		expect(french).not.toBe(english);
	});
});
