import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createFakeExtension } from '$test-support/fake-extension';
import { en } from '$technical/i18n/messages/en';
import {
	BADGE_CLEAR_DELAY_MS,
	NEEDS_SETTINGS,
	OUTCOME_BADGE,
	OUTCOME_MESSAGE,
	showOutcomeBadge
} from './save-feedback';
import type { SaveOutcome } from './save-page';

const OUTCOMES: SaveOutcome[] = [
	'saved',
	'already_saved',
	'unsupported',
	'unconfigured',
	'unauthenticated',
	'failed'
];

describe('outcome tables', () => {
	it.each(OUTCOMES)('has a badge and an existing message for %s', (outcome) => {
		expect(OUTCOME_BADGE[outcome].text).not.toBe('');
		expect(en[OUTCOME_MESSAGE[outcome]]).toBeTruthy();
	});

	it('gives the three success-or-not families three distinct looks', () => {
		expect(OUTCOME_BADGE.saved.text).not.toBe(OUTCOME_BADGE.already_saved.text);
		expect(OUTCOME_BADGE.saved.text).not.toBe(OUTCOME_BADGE.failed.text);
	});

	it('sends the reader to the settings only when the settings can fix it', () => {
		expect([...NEEDS_SETTINGS].sort()).toEqual(['unauthenticated', 'unconfigured']);
	});
});

describe('showOutcomeBadge', () => {
	beforeEach(() => {
		vi.useFakeTimers();
	});

	afterEach(() => {
		vi.useRealTimers();
	});

	it('paints the badge, sets the tooltip, then clears the badge', async () => {
		const { extension, badge } = createFakeExtension();
		await showOutcomeBadge(extension.action, 'saved', 'Saved to Lumia');
		expect(badge).toEqual({ text: '✓', color: OUTCOME_BADGE.saved.color, title: 'Saved to Lumia' });

		await vi.advanceTimersByTimeAsync(BADGE_CLEAR_DELAY_MS);
		expect(badge.text).toBe('');
	});
});
