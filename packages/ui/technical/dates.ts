import { Temporal } from 'temporal-polyfill';

/**
 * Formats a UTC instant as a calendar date in the reader's own timezone. The backend only knows
 * UTC, but "today" and "yesterday" are boundaries that depend on where the reader is: a midnight
 * article in Paris is still the previous evening in New York.
 */
export function formatPublishedDate(
	publishedAt: string,
	locale: string,
	options: Intl.DateTimeFormatOptions
): string {
	const zoned = Temporal.Instant.from(publishedAt).toZonedDateTimeISO(Temporal.Now.timeZoneId());
	return zoned.toLocaleString(locale, options);
}
