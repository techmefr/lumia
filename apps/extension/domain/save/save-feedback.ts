import type { ExtensionApi } from '$technical/browser/extension-api';
import type { MessageKey } from '$technical/i18n/i18n';
import type { SaveOutcome } from './save-page';

export const BADGE_CLEAR_DELAY_MS = 4000;

export const OUTCOME_MESSAGE: Record<SaveOutcome, MessageKey> = {
	saved: 'save.saved',
	already_saved: 'save.alreadySaved',
	unsupported: 'save.unsupported',
	unconfigured: 'save.unconfigured',
	unauthenticated: 'save.unauthenticated',
	failed: 'save.failed'
};

export const OUTCOME_BADGE: Record<SaveOutcome, { text: string; color: string }> = {
	saved: { text: '✓', color: '#16a34a' },
	already_saved: { text: '=', color: '#2563eb' },
	unsupported: { text: '!', color: '#d97706' },
	unconfigured: { text: '!', color: '#d97706' },
	unauthenticated: { text: '!', color: '#d97706' },
	failed: { text: '✕', color: '#dc2626' }
};

export const NEEDS_SETTINGS: ReadonlySet<SaveOutcome> = new Set<SaveOutcome>([
	'unconfigured',
	'unauthenticated'
]);

export async function showOutcomeBadge(
	action: ExtensionApi['action'],
	outcome: SaveOutcome,
	title: string
): Promise<void> {
	const badge = OUTCOME_BADGE[outcome];
	await action.setBadgeBackgroundColor({ color: badge.color });
	await action.setBadgeText({ text: badge.text });
	await action.setTitle({ title });
	setTimeout(() => {
		void action.setBadgeText({ text: '' });
	}, BADGE_CLEAR_DELAY_MS);
}
