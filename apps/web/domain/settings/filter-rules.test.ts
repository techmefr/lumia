import type { FilterMode, FilterRule } from '@lumia/core';
import { fireEvent, render } from '@testing-library/svelte';
import { toasts } from '@lumia/ui';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import FilterRules from './filter-rules.svelte';

// The client is the app's http boundary, so it is what gets replaced. Everything asserted below is
// what the panel shows and what it asked the api for.
vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		recommendation: {
			listFilterRules: vi.fn(),
			addFilterRule: vi.fn(),
			deleteFilterRule: vi.fn()
		}
	}
}));

const api = vi.mocked(lumia.recommendation);

function rule(id: string, term: string, mode: FilterMode): FilterRule {
	return { id, term, mode } as FilterRule;
}

const RULES = [
	rule('r1', 'kiosque', 'boost'),
	rule('r2', 'crypto', 'mute'),
	rule('r3', 'papier', 'boost')
];

function panel() {
	const { container } = render(FilterRules);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		term: () => q<HTMLInputElement>('[data-test-input]')!,
		mode: () => q<HTMLSelectElement>('[data-test-rule-mode]')!,
		submit: () => q<HTMLButtonElement>('[data-test-rule-submit]')!,
		error: () => q('[data-test-rules-error]'),
		chips: () =>
			[...container.querySelectorAll<HTMLElement>('[data-test-rule]')].map((node) => ({
				id: node.dataset.testRule,
				mode: node.dataset.testRuleModeOf,
				text: node.textContent?.trim().replace(/\s+/g, ' ')
			})),
		chip: (id: string) => q<HTMLButtonElement>(`[data-test-rule="${id}"]`),
		emptyGroups: () => [...container.querySelectorAll('[data-test-rule-group-empty]')]
	};
}

/** The panel loads on mount, so every assertion waits for the list rather than for a delay. */
async function loaded() {
	const view = panel();
	await vi.waitFor(() => expect(api.listFilterRules).toHaveBeenCalled());
	return view;
}

beforeEach(() => {
	api.listFilterRules.mockResolvedValue(RULES);
	api.addFilterRule.mockReset();
	api.deleteFilterRule.mockReset();
});

afterEach(() => {
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.clearAllMocks();
});

describe('the rules it shows', () => {
	it('lists the rules the account has', async () => {
		const view = await loaded();
		await vi.waitFor(() => expect(view.chips()).toHaveLength(3));
	});

	// Boosted and muted are opposite effects, so they are shown as two separate groups: a single
	// list of chips would give no way to tell which term lifts an article and which buries it.
	it('splits them by effect', async () => {
		const view = await loaded();
		await vi.waitFor(() => expect(view.chips()).toHaveLength(3));

		expect(view.chips().filter((chip) => chip.mode === 'boost')).toHaveLength(2);
		expect(view.chips().filter((chip) => chip.mode === 'mute')).toHaveLength(1);
	});

	it('shows the term of each rule', async () => {
		const view = await loaded();
		await vi.waitFor(() => expect(view.chip('r1')?.textContent).toContain('kiosque'));
	});

	// The chip is a button whose only visible content is a term and a cross: without the spelled
	// out label, a screen reader announces "kiosque" and nothing about what pressing it does.
	it('says what pressing a chip does', async () => {
		const view = await loaded();
		await vi.waitFor(() => expect(view.chip('r1')).not.toBeNull());

		expect(view.chip('r1')?.querySelector('.sr-only')?.textContent).toContain('kiosque');
	});

	it('says a group is empty rather than leaving a blank space', async () => {
		api.listFilterRules.mockResolvedValue([]);
		const view = await loaded();

		await vi.waitFor(() => expect(view.emptyGroups()).toHaveLength(2));
	});

	it('says so when the rules could not be loaded', async () => {
		api.listFilterRules.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.error()?.getAttribute('role')).toBe('alert');
	});
});

describe('adding a rule', () => {
	it('sends the term and the effect that were chosen', async () => {
		api.addFilterRule.mockResolvedValue(rule('r4', 'kiosques', 'mute'));
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.change(view.mode(), { target: { value: 'mute' } });
		await fireEvent.click(view.submit());

		expect(api.addFilterRule).toHaveBeenCalledWith('kiosques', 'mute');
	});

	it('boosts unless told otherwise', async () => {
		api.addFilterRule.mockResolvedValue(rule('r4', 'kiosques', 'boost'));
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.click(view.submit());

		expect(api.addFilterRule).toHaveBeenCalledWith('kiosques', 'boost');
	});

	it('shows the new rule without reloading the list', async () => {
		api.addFilterRule.mockResolvedValue(rule('r4', 'kiosques', 'mute'));
		const view = await loaded();
		await vi.waitFor(() => expect(view.chips()).toHaveLength(3));

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.click(view.submit());

		await vi.waitFor(() => expect(view.chip('r4')).not.toBeNull());
		expect(api.listFilterRules).toHaveBeenCalledTimes(1);
	});

	it('clears the field, ready for the next one', async () => {
		api.addFilterRule.mockResolvedValue(rule('r4', 'kiosques', 'boost'));
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.click(view.submit());

		await vi.waitFor(() => expect(view.term().value).toBe(''));
	});

	it('trims what was typed', async () => {
		api.addFilterRule.mockResolvedValue(rule('r4', 'kiosques', 'boost'));
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value: '  kiosques  ' } });
		await fireEvent.click(view.submit());

		expect(api.addFilterRule).toHaveBeenCalledWith('kiosques', 'boost');
	});

	// A one-letter term would match half the library, boosting or burying almost everything.
	it.each(['', ' ', 'a', ' a '])('refuses %p as too short to be a rule', async (value) => {
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value } });
		await fireEvent.click(view.submit());

		expect(api.addFilterRule).not.toHaveBeenCalled();
		await vi.waitFor(() => expect(view.error()).not.toBeNull());
	});

	// The api is idempotent, so re-adding a term answers with the rule that already exists. Adding
	// it to the list again would show the same chip twice and one of them would not delete.
	it('does not show a rule twice when it was already there', async () => {
		api.addFilterRule.mockResolvedValue(RULES[0]);
		const view = await loaded();
		await vi.waitFor(() => expect(view.chips()).toHaveLength(3));

		await fireEvent.input(view.term(), { target: { value: 'kiosque' } });
		await fireEvent.click(view.submit());

		await vi.waitFor(() => expect(api.addFilterRule).toHaveBeenCalled());
		expect(view.chips().filter((chip) => chip.id === 'r1')).toHaveLength(1);
	});

	it('says so when the rule could not be saved', async () => {
		api.addFilterRule.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.click(view.submit());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
	});

	it('keeps what was typed when saving failed, so it is not lost', async () => {
		api.addFilterRule.mockRejectedValue(new Error('offline'));
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.click(view.submit());

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.term().value).toBe('kiosques');
	});

	it('clears a previous error once a rule goes through', async () => {
		api.addFilterRule.mockRejectedValueOnce(new Error('offline'));
		api.addFilterRule.mockResolvedValueOnce(rule('r4', 'kiosques', 'boost'));
		const view = await loaded();

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.click(view.submit());
		await vi.waitFor(() => expect(view.error()).not.toBeNull());

		await fireEvent.input(view.term(), { target: { value: 'kiosques' } });
		await fireEvent.click(view.submit());

		await vi.waitFor(() => expect(view.error()).toBeNull());
	});
});

describe('removing a rule', () => {
	it('deletes the rule whose chip was pressed', async () => {
		api.deleteFilterRule.mockResolvedValue(undefined);
		const view = await loaded();
		await vi.waitFor(() => expect(view.chip('r2')).not.toBeNull());

		await fireEvent.click(view.chip('r2')!);

		expect(api.deleteFilterRule).toHaveBeenCalledWith('r2');
	});

	it('takes the chip off the list', async () => {
		api.deleteFilterRule.mockResolvedValue(undefined);
		const view = await loaded();
		await vi.waitFor(() => expect(view.chips()).toHaveLength(3));

		await fireEvent.click(view.chip('r2')!);

		await vi.waitFor(() => expect(view.chip('r2')).toBeNull());
		expect(view.chips()).toHaveLength(2);
	});

	// The rule is still there if the api refused, so the chip has to stay: removing it would show
	// a filter as gone while it keeps burying articles.
	it('keeps the chip when the deletion failed', async () => {
		api.deleteFilterRule.mockRejectedValue(new Error('offline'));
		const view = await loaded();
		await vi.waitFor(() => expect(view.chip('r2')).not.toBeNull());

		await fireEvent.click(view.chip('r2')!);

		await vi.waitFor(() => expect(toasts.toasts).toHaveLength(1));
		expect(toasts.toasts[0].tone).toBe('destructive');
		expect(view.chip('r2')).not.toBeNull();
	});
});
