import { cleanup, fireEvent, render, waitFor } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { goto } from '$app/navigation';
import { lumia } from '$technical/api/client';
import { getLocale } from '$technical/i18n/i18n.svelte';
import {
	areShortcutsEnabled,
	setShortcutsEnabled
} from '$technical/keyboard/shortcuts-store.svelte.js';
import {
	ACCENT_PRESETS,
	FONT_PAIR_PRESETS,
	FONT_SCALE_PRESETS,
	getAccentHue,
	getFontPair,
	getFontScale,
	getTheme,
	isReadingComfort
} from '$technical/theme/theme-store.svelte.js';
import { instanceSettings, me } from '../test-support/fixtures';
import SettingsPage from './+page.svelte';

vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: {
			isAuthenticated: vi.fn(() => true),
			getMe: vi.fn(),
			updateMe: vi.fn(),
			changePassword: vi.fn(),
			startTotpEnrolment: vi.fn(),
			confirmTotpEnrolment: vi.fn(),
			renewRecoveryCodes: vi.fn(),
			disableTotp: vi.fn()
		},
		recommendation: { listFilterRules: vi.fn() },
		instance: { getSettings: vi.fn(), listAccounts: vi.fn(), listAccessRequests: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

const READER = me();

function settingsPage() {
	const { container } = render(SettingsPage);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		container,
		locale: () => q<HTMLSelectElement>('#ui-locale')!,
		themeInput: (value: string) => q<HTMLInputElement>(`input[name="theme"][value="${value}"]`)!,
		accentInput: (id: string) => q<HTMLInputElement>(`input[name="accent"][value="${id}"]`)!,
		pairInput: (id: string) => q<HTMLInputElement>(`input[name="font-pair"][value="${id}"]`)!,
		scaleInput: (id: string) => q<HTMLInputElement>(`input[name="font-scale"][value="${id}"]`)!,
		comfort: () => q<HTMLButtonElement>('[data-test-comfort]')!,
		passwordPanel: () => q('[data-test-password-form]'),
		totpPanel: () => q('[data-test-totp-status], [data-test-totp-enable]'),
		shortcuts: () => q<HTMLButtonElement>('[data-test-shortcuts-toggle]')!,
		instanceAdmin: () => q('[data-test-instance-admin]')
	};
}

beforeEach(() => {
	api.user.isAuthenticated.mockReturnValue(true);
	api.user.getMe.mockResolvedValue(READER);
	api.recommendation.listFilterRules.mockResolvedValue([]);
	api.instance.getSettings.mockResolvedValue(instanceSettings());
	api.instance.listAccounts.mockResolvedValue([]);
	api.instance.listAccessRequests.mockResolvedValue([]);
});

afterEach(() => {
	cleanup();
	setShortcutsEnabled(true);
	vi.clearAllMocks();
});

describe('opening the settings', () => {
	it('sends a reader with no session to the sign-in screen', async () => {
		api.user.isAuthenticated.mockReturnValue(false);

		settingsPage();

		await waitFor(() => expect(goto).toHaveBeenCalled());
		expect(String(vi.mocked(goto).mock.calls[0][0])).toContain('/login');
	});

	it('offers the password panel to every reader', async () => {
		const view = settingsPage();

		await waitFor(() => expect(view.passwordPanel()).not.toBeNull());
	});

	it('offers two-factor authentication to every reader', async () => {
		const view = settingsPage();

		await waitFor(() => expect(view.totpPanel()).not.toBeNull());
	});
});

describe('the keyboard shortcuts switch', () => {
	// WCAG 2.1.4: a key that acts on its own press has to be silenceable, because speech input turns
	// dictated words into a stream of them.
	it('turns the single-key shortcuts off and back on', async () => {
		const view = settingsPage();
		await waitFor(() => expect(view.shortcuts()).not.toBeNull());

		await fireEvent.click(view.shortcuts());
		expect(areShortcutsEnabled()).toBe(false);
		await waitFor(() => expect(view.shortcuts().getAttribute('aria-pressed')).toBe('false'));

		await fireEvent.click(view.shortcuts());
		expect(areShortcutsEnabled()).toBe(true);
	});

	// The store is read once at module load, so the panel has to hydrate from the setting rather
	// than assume the default every time the screen is opened.
	it('opens showing the choice already made', async () => {
		setShortcutsEnabled(false);
		const view = settingsPage();

		await waitFor(() => expect(view.shortcuts().getAttribute('aria-pressed')).toBe('false'));
	});
});

describe('choosing how the app looks', () => {
	it('stores the theme the reader picked', async () => {
		const view = settingsPage();
		await waitFor(() => expect(view.themeInput('dark')).not.toBeNull());

		await fireEvent.change(view.themeInput('dark'));

		expect(getTheme()).toBe('dark');
		await waitFor(() => expect(view.themeInput('dark').checked).toBe(true));
	});

	it('stores the accent the reader picked', async () => {
		const preset = ACCENT_PRESETS[3];
		const view = settingsPage();
		await waitFor(() => expect(view.accentInput(preset.id)).not.toBeNull());

		await fireEvent.change(view.accentInput(preset.id));

		expect(getAccentHue()).toBe(preset.hue);
	});

	it('stores the font pair the reader picked', async () => {
		const preset = FONT_PAIR_PRESETS[2];
		const view = settingsPage();
		await waitFor(() => expect(view.pairInput(preset.id)).not.toBeNull());

		await fireEvent.change(view.pairInput(preset.id));

		expect(getFontPair()).toBe(preset.id);
	});

	it('stores the text size the reader picked', async () => {
		const preset = FONT_SCALE_PRESETS[4];
		const view = settingsPage();
		await waitFor(() => expect(view.scaleInput(preset.id)).not.toBeNull());

		await fireEvent.change(view.scaleInput(preset.id));

		expect(getFontScale()).toBe(preset.scale);
	});

	it('turns reading comfort on and back off', async () => {
		const view = settingsPage();
		await waitFor(() => expect(view.comfort()).not.toBeNull());

		await fireEvent.click(view.comfort());
		expect(isReadingComfort()).toBe(true);

		await fireEvent.click(view.comfort());
		expect(isReadingComfort()).toBe(false);
	});

	it('changes the interface language', async () => {
		const view = settingsPage();
		await waitFor(() => expect(view.locale()).not.toBeNull());

		await fireEvent.change(view.locale(), { target: { value: 'de' } });

		expect(getLocale()).toBe('de');
		await waitFor(() => expect(view.locale().value).toBe('de'));
	});
});

describe('the instance administration panel', () => {
	// The API is the real guard; hiding the panel only spares a member a screenful of 403s.
	it('stays hidden from a plain member', async () => {
		const view = settingsPage();
		await waitFor(() => expect(api.user.getMe).toHaveBeenCalled());

		expect(view.instanceAdmin()).toBeNull();
	});

	it('appears for an administrator', async () => {
		api.user.getMe.mockResolvedValue(me({ role: 'admin' }));
		const view = settingsPage();

		await waitFor(() => expect(view.instanceAdmin()).not.toBeNull());
	});

	it('stays hidden when the account cannot be fetched', async () => {
		api.user.getMe.mockRejectedValue(new Error('offline'));
		const view = settingsPage();

		await waitFor(() => expect(api.user.getMe).toHaveBeenCalled());
		expect(view.instanceAdmin()).toBeNull();
	});
});
