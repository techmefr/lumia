/**
 * Browser notifications for new unread articles.
 *
 * Deliberately client-side and poll-based: Lumia has no push server, and adding one would mean
 * routing every reader's device token through a third-party push service — the opposite of what a
 * self-hosted reader is for. So the app asks its own instance for the unread counts on an interval
 * while a tab is open, and notifies when the total goes up.
 */

import { t } from '../i18n/i18n.svelte';

const SETTINGS_KEY = 'lumia-notifications';
const BASELINE_KEY = 'lumia-notifications-baseline';

export interface NotificationSettings {
	enabled: boolean;
	/** How often the unread counts are re-checked, in minutes. */
	intervalMinutes: number;
	/** Below this many new articles, nothing is shown: a single item is not worth interrupting for. */
	threshold: number;
	/** Quiet hours, as hours of the day. Equal values mean "never quiet". */
	quietFromHour: number;
	quietToHour: number;
}

export const INTERVAL_OPTIONS = [15, 30, 60, 180];

const DEFAULTS: NotificationSettings = {
	enabled: false,
	intervalMinutes: 30,
	threshold: 3,
	quietFromHour: 22,
	quietToHour: 8
};

function readSettings(): NotificationSettings {
	if (typeof localStorage === 'undefined') return { ...DEFAULTS };
	try {
		const stored = localStorage.getItem(SETTINGS_KEY);
		if (!stored) return { ...DEFAULTS };
		return { ...DEFAULTS, ...(JSON.parse(stored) as Partial<NotificationSettings>) };
	} catch {
		return { ...DEFAULTS };
	}
}

let settings = $state<NotificationSettings>(readSettings());

export function getNotificationSettings(): NotificationSettings {
	return settings;
}

export function updateNotificationSettings(patch: Partial<NotificationSettings>): void {
	settings = { ...settings, ...patch };
	try {
		localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
	} catch {
		/* private browsing: the settings just won't survive a reload */
	}
}

/** 'unsupported' distinguishes a browser without the API from one that refused. */
export type PermissionState = 'unsupported' | 'default' | 'granted' | 'denied';

export function permissionState(): PermissionState {
	if (typeof Notification === 'undefined') return 'unsupported';
	return Notification.permission as Exclude<PermissionState, 'unsupported'>;
}

export async function requestPermission(): Promise<PermissionState> {
	if (typeof Notification === 'undefined') return 'unsupported';
	// Must be called from a user gesture, which is why this is not done on mount.
	return (await Notification.requestPermission()) as Exclude<PermissionState, 'unsupported'>;
}

/** True inside the quiet window, which may wrap past midnight. */
export function isQuietHour(date: Date, from: number, to: number): boolean {
	if (from === to) return false;
	const hour = date.getHours();
	return from < to ? hour >= from && hour < to : hour >= from || hour < to;
}

function readBaseline(): number | null {
	try {
		const stored = localStorage.getItem(BASELINE_KEY);
		return stored === null ? null : Number(stored);
	} catch {
		return null;
	}
}

function writeBaseline(total: number): void {
	try {
		localStorage.setItem(BASELINE_KEY, String(total));
	} catch {
		/* nothing to remember */
	}
}

/**
 * Decides what a poll should do. Split out from the timer so the rule is testable and so a first
 * poll after enabling only records where the counter stood — it must not fire on the whole backlog.
 */
export function notificationFor(
	total: number,
	baseline: number | null,
	config: NotificationSettings,
	now: Date
): string | null {
	if (baseline === null || total <= baseline) return null;
	const fresh = total - baseline;
	if (fresh < config.threshold) return null;
	if (isQuietHour(now, config.quietFromHour, config.quietToHour)) return null;
	return fresh === 1
		? t('notifications.newArticle')
		: t('notifications.newArticles', { count: fresh });
}

/**
 * Starts the poll. Returns a teardown, so the caller (the root layout) owns the lifetime.
 *
 * `fetchTotal` is injected rather than importing the client here: technical/ must not depend on the
 * app's wiring, and it keeps this testable without a fake HTTP layer.
 */
export function watchUnread(fetchTotal: () => Promise<number>): () => void {
	let timer: ReturnType<typeof setInterval> | null = null;
	let stopped = false;

	async function poll(): Promise<void> {
		if (stopped || !settings.enabled || permissionState() !== 'granted') return;
		if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
			// Looking at the app is not an interruption worth a system notification.
			try {
				writeBaseline(await fetchTotal());
			} catch {
				/* offline or logged out: the next tick tries again */
			}
			return;
		}
		try {
			const total = await fetchTotal();
			const message = notificationFor(total, readBaseline(), settings, new Date());
			writeBaseline(total);
			if (message) new Notification('Lumia', { body: message, tag: 'lumia-unread' });
		} catch {
			/* offline or logged out: the next tick tries again */
		}
	}

	function schedule(): void {
		if (timer !== null) clearInterval(timer);
		timer = setInterval(poll, settings.intervalMinutes * 60_000);
	}

	// The first poll only sets the baseline, whatever the tab's visibility, so enabling
	// notifications never announces the backlog that was already there.
	void fetchTotal()
		.then(writeBaseline)
		.catch(() => {});
	schedule();

	// The interval is a setting: re-read it when the tab comes back rather than on every change.
	const onVisible = () => schedule();
	document.addEventListener('visibilitychange', onVisible);

	return () => {
		stopped = true;
		if (timer !== null) clearInterval(timer);
		document.removeEventListener('visibilitychange', onVisible);
	};
}
