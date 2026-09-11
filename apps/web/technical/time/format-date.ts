import { Temporal } from 'temporal-polyfill';

/**
 * Formats a backend ISO instant as a short date in the reader's own timezone.
 *
 * Miniflux and the API always talk UTC; showing that offset back to the reader instead of their
 * local day would make "depuis le" claims read as being off by however many hours their zone sits
 * from UTC.
 */
export function formatDateInUserTimezone(isoInstant: string, locale: string): string {
	const zoned = Temporal.Instant.from(isoInstant).toZonedDateTimeISO(Temporal.Now.timeZoneId());
	return new Intl.DateTimeFormat(locale, {
		year: 'numeric',
		month: 'short',
		day: 'numeric'
	}).format(new Date(zoned.epochMilliseconds));
}
