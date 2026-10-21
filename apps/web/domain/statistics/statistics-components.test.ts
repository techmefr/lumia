import type { DailyReading, FeedEngagement } from '@lumia/core';
import { cleanup, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it } from 'vitest';
import DailyBars from './daily-bars.svelte';
import FeedEngagementTable from './feed-engagement-table.svelte';
import RankedBars from './ranked-bars.svelte';

afterEach(cleanup);

const DAILY: DailyReading[] = [
	{ day: '2026-10-19', articles_read: 0, reading_minutes: 0 },
	{ day: '2026-10-20', articles_read: 4, reading_minutes: 12 },
	{ day: '2026-10-21', articles_read: 2, reading_minutes: 5 }
];

function bars(daily: DailyReading[]) {
	const { container } = render(DailyBars, { daily });
	return {
		chart: () => container.querySelector('[data-test-daily-chart]')!,
		bar: (day: string) => container.querySelector<HTMLElement>(`[data-test-daily-bar="${day}"]`)!,
		rows: () => [...container.querySelectorAll('[data-test-daily-table] tbody tr')],
		summary: () => container.querySelector('[data-test-daily-summary]')!.textContent
	};
}

describe('the daily chart', () => {
	it('draws one bar per day', () => {
		const view = bars(DAILY);
		expect(DAILY.every((entry) => view.bar(entry.day) !== null)).toBe(true);
	});

	it('scales every bar against the busiest day', () => {
		const view = bars(DAILY);
		expect(view.bar('2026-10-20').style.height).toBe('100%');
		expect(view.bar('2026-10-21').style.height).toBe('50%');
	});

	it('gives the chart a text alternative naming the total and the busiest day', () => {
		const view = bars(DAILY);
		const label = view.chart().getAttribute('aria-label')!;
		expect(view.chart().getAttribute('role')).toBe('img');
		expect(label).toContain('6');
		expect(label).toContain('2026-10-20');
	});

	it('backs the picture with a table carrying the figures', () => {
		const view = bars(DAILY);
		expect(view.rows()).toHaveLength(3);
		expect(view.rows()[1].textContent).toContain('12');
	});

	it('says nothing was read instead of drawing an empty chart label', () => {
		const view = bars(DAILY.map((entry) => ({ ...entry, articles_read: 0 })));
		expect(view.chart().getAttribute('aria-label')).toBe(view.summary());
		expect(view.chart().getAttribute('aria-label')).not.toContain('2026');
	});
});

function ranked(items: { key: string; label: string; count: number }[]) {
	const { container } = render(RankedBars, { title: 'Top', items, testId: 'feeds' });
	return {
		item: (key: string) => container.querySelector(`[data-test-ranked-item="${key}"]`),
		empty: () => container.querySelector('[data-test-ranked-empty]'),
		fill: (key: string) =>
			container.querySelector(`[data-test-ranked-item="${key}"] [style]`) as HTMLElement
	};
}

describe('a ranked list', () => {
	it('shows each label with its count as text', () => {
		const view = ranked([{ key: 'a', label: 'Fibre', count: 7 }]);
		expect(view.item('a')!.textContent).toContain('Fibre');
		expect(view.item('a')!.textContent).toContain('7');
	});

	it('sizes the bars against the first entry', () => {
		const view = ranked([
			{ key: 'a', label: 'A', count: 8 },
			{ key: 'b', label: 'B', count: 2 }
		]);
		expect(view.fill('a').style.width).toBe('100%');
		expect(view.fill('b').style.width).toBe('25%');
	});

	it('says there is nothing to show when the list is empty', () => {
		expect(ranked([]).empty()).not.toBeNull();
	});
});

function engagement(overrides: Partial<FeedEngagement> = {}): FeedEngagement {
	return {
		feed_id: 'feed-1',
		title: 'Noisy',
		received: 4,
		read: 1,
		ignored: 3,
		read_ratio: 0.25,
		...overrides
	};
}

describe('the feed engagement table', () => {
	it('lists the counts and the share read of each feed', () => {
		const { container } = render(FeedEngagementTable, { feeds: [engagement()] });
		const row = container.querySelector('[data-test-engagement-row="feed-1"]')!;
		expect(row.textContent).toContain('Noisy');
		expect(row.textContent).toMatch(/4\s*1\s*3/);
		expect(row.querySelector('[data-test-engagement-ratio]')!.textContent).toContain('25');
	});

	it('shows an empty message when no feed delivered anything', () => {
		const { container } = render(FeedEngagementTable, { feeds: [] });
		expect(container.querySelector('[data-test-engagement-empty]')).not.toBeNull();
		expect(container.querySelector('[data-test-engagement]')).toBeNull();
	});
});
