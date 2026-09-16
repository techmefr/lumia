import { ApiError, type Me } from '@lumia/core';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import TotpSettings from './totp-settings.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		user: {
			getMe: vi.fn(),
			startTotpEnrolment: vi.fn(),
			confirmTotpEnrolment: vi.fn(),
			renewRecoveryCodes: vi.fn(),
			disableTotp: vi.fn()
		}
	}
}));

// The QR renderer touches a canvas, which jsdom does not provide; the panel only ever puts the
// string it returns into a src attribute.
vi.mock('qrcode', () => ({ default: { toDataURL: vi.fn().mockResolvedValue('data:image/png,qr') } }));

const api = vi.mocked(lumia.user);

const RECOVERY_CODES = ['aaaa-bbbb-cccc-dddd-eeee', 'ffff-0000-1111-2222-3333'];

function me(overrides: Partial<Me> = {}): Me {
	return {
		id: 'user-1',
		email: 'reader@example.test',
		role: 'member',
		password_set: true,
		totp_enabled: false,
		recovery_codes_left: 0,
		...overrides
	} as Me;
}

function panel() {
	const { container } = render(TotpSettings);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		status: () => q('[data-test-totp-status]'),
		enable: () => q<HTMLButtonElement>('[data-test-totp-enable]')!,
		qr: () => q<HTMLImageElement>('[data-test-totp-qr]'),
		secret: () => q('[data-test-totp-secret]'),
		confirmForm: () => q<HTMLFormElement>('[data-test-totp-confirm-form]'),
		code: () => q<HTMLInputElement>('[data-test-totp-code]')!,
		error: () => q('[data-test-totp-error]'),
		recoveryCodes: () => q('[data-test-recovery-codes]'),
		recoveryDone: () => q<HTMLButtonElement>('[data-test-recovery-done]')!,
		codesLeft: () => q('[data-test-totp-codes-left]'),
		renewOpen: () => q<HTMLButtonElement>('[data-test-totp-renew-open]')!,
		renewForm: () => q<HTMLFormElement>('[data-test-totp-renew-form]'),
		renewCode: () => q<HTMLInputElement>('[data-test-totp-renew-code]')!,
		disableOpen: () => q<HTMLButtonElement>('[data-test-totp-disable-open]')!,
		disableForm: () => q<HTMLFormElement>('[data-test-totp-disable-form]'),
		disablePassword: () => q<HTMLInputElement>('[data-test-totp-disable-password]'),
		disableCode: () => q<HTMLInputElement>('[data-test-totp-disable-code]')
	};
}

async function loaded(account: Me = me()) {
	api.getMe.mockResolvedValue(account);
	const view = panel();
	// The panel renders its "off" state before /me answers, so waiting on the status alone would
	// let a test read the placeholder rather than the account it asked for.
	await vi.waitFor(() => expect(view.codesLeft() !== null).toBe(account.totp_enabled));
	return view;
}

async function enrol(view: ReturnType<typeof panel>) {
	api.startTotpEnrolment.mockResolvedValue({
		secret: 'JBSWY3DPEHPK3PXP',
		otpauth_uri: 'otpauth://totp/Lumia:reader@example.test?secret=JBSWY3DPEHPK3PXP'
	});
	await fireEvent.click(view.enable());
	await vi.waitFor(() => expect(view.confirmForm()).not.toBeNull());
}

function refused(detail: string) {
	return new ApiError(401, { detail });
}

beforeEach(() => {
	api.getMe.mockReset();
	api.startTotpEnrolment.mockReset();
	api.confirmTotpEnrolment.mockReset();
	api.renewRecoveryCodes.mockReset();
	api.disableTotp.mockReset();
});

afterEach(() => {
	vi.clearAllMocks();
});

describe('enrolment', () => {
	it('offers to turn the second factor on when the account has none', async () => {
		const view = await loaded();

		expect(view.enable()).not.toBeNull();
		expect(view.confirmForm()).toBeNull();
	});

	it('shows a qr code and the same secret in typeable form', async () => {
		const view = await loaded();

		await enrol(view);

		expect(view.qr()?.src).toBe('data:image/png,qr');
		expect(view.secret()?.textContent).toContain('JBSWY3DPEHPK3PXP');
	});

	it('asks for a code before anything is switched on', async () => {
		const view = await loaded();

		await enrol(view);

		expect(api.confirmTotpEnrolment).not.toHaveBeenCalled();
		expect(view.code()).not.toBeNull();
	});

	it('shows the recovery codes once the enrolment is confirmed', async () => {
		const view = await loaded();
		await enrol(view);
		api.confirmTotpEnrolment.mockResolvedValue(RECOVERY_CODES);
		api.getMe.mockResolvedValue(me({ totp_enabled: true, recovery_codes_left: 2 }));

		await fireEvent.input(view.code(), { target: { value: '123456' } });
		await fireEvent.submit(view.confirmForm()!);

		await vi.waitFor(() => expect(view.recoveryCodes()).not.toBeNull());
		expect(view.recoveryCodes()?.textContent).toContain(RECOVERY_CODES[0]);
		expect(view.recoveryCodes()?.textContent).toContain(RECOVERY_CODES[1]);
	});

	it('keeps the form open and says so when the code is wrong', async () => {
		const view = await loaded();
		await enrol(view);
		api.confirmTotpEnrolment.mockRejectedValue(refused('invalid_totp_code'));

		await fireEvent.input(view.code(), { target: { value: '000000' } });
		await fireEvent.submit(view.confirmForm()!);

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.recoveryCodes()).toBeNull();
		expect(view.confirmForm()).not.toBeNull();
	});

	it('returns to the panel once the codes have been acknowledged', async () => {
		const view = await loaded();
		await enrol(view);
		api.confirmTotpEnrolment.mockResolvedValue(RECOVERY_CODES);
		api.getMe.mockResolvedValue(me({ totp_enabled: true, recovery_codes_left: 2 }));
		await fireEvent.input(view.code(), { target: { value: '123456' } });
		await fireEvent.submit(view.confirmForm()!);
		await vi.waitFor(() => expect(view.recoveryCodes()).not.toBeNull());

		await fireEvent.click(view.recoveryDone());

		await vi.waitFor(() => expect(view.recoveryCodes()).toBeNull());
		expect(view.disableOpen()).not.toBeNull();
	});
});

describe('an account that already has it on', () => {
	it('says how many recovery codes are left', async () => {
		const view = await loaded(me({ totp_enabled: true, recovery_codes_left: 7 }));

		expect(view.codesLeft()?.textContent).toContain('7');
	});

	it('warns when the set is nearly spent', async () => {
		const view = await loaded(me({ totp_enabled: true, recovery_codes_left: 1 }));

		expect(view.codesLeft()?.className).toContain('destructive');
	});

	it('renews the recovery codes against a live code', async () => {
		const view = await loaded(me({ totp_enabled: true, recovery_codes_left: 1 }));
		api.renewRecoveryCodes.mockResolvedValue(RECOVERY_CODES);
		await fireEvent.click(view.renewOpen());

		await fireEvent.input(view.renewCode(), { target: { value: '123456' } });
		await fireEvent.submit(view.renewForm()!);

		await vi.waitFor(() => expect(view.recoveryCodes()).not.toBeNull());
		expect(api.renewRecoveryCodes).toHaveBeenCalledWith('123456');
	});
});

describe('turning it off', () => {
	it('asks for the password rather than taking the session on trust', async () => {
		const view = await loaded(me({ totp_enabled: true, recovery_codes_left: 5 }));

		await fireEvent.click(view.disableOpen());

		expect(view.disablePassword()).not.toBeNull();
		expect(api.disableTotp).not.toHaveBeenCalled();
	});

	it('asks for a code instead when the account has no password', async () => {
		const view = await loaded(
			me({ totp_enabled: true, recovery_codes_left: 5, password_set: false })
		);

		await fireEvent.click(view.disableOpen());

		expect(view.disablePassword()).toBeNull();
		expect(view.disableCode()).not.toBeNull();
	});

	it('turns it off once the password is given', async () => {
		const view = await loaded(me({ totp_enabled: true, recovery_codes_left: 5 }));
		api.disableTotp.mockResolvedValue(undefined);
		await fireEvent.click(view.disableOpen());

		await fireEvent.input(view.disablePassword()!, { target: { value: 'correct-horse' } });
		api.getMe.mockResolvedValue(me());
		await fireEvent.submit(view.disableForm()!);

		await vi.waitFor(() => expect(api.disableTotp).toHaveBeenCalledWith('correct-horse', {}));
	});

	it('leaves it on and says so when the password is wrong', async () => {
		const view = await loaded(me({ totp_enabled: true, recovery_codes_left: 5 }));
		api.disableTotp.mockRejectedValue(refused('Unauthorized'));
		await fireEvent.click(view.disableOpen());

		await fireEvent.input(view.disablePassword()!, { target: { value: 'not-the-one' } });
		await fireEvent.submit(view.disableForm()!);

		await vi.waitFor(() => expect(view.error()).not.toBeNull());
		expect(view.disableForm()).not.toBeNull();
	});
});
