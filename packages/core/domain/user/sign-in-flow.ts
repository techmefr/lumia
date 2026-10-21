import { ApiError } from '../../technical/http-client';
import { secondFactorFailure, type UserApi } from './api';
import type { SecondFactor } from './types';

export type SignInStep = 'credentials' | 'code' | 'recovery';

export type SignInOutcome = 'signed_in' | 'challenge' | 'wrong_code' | 'bad_credentials' | 'failed';

type Proof = { kind: 'password'; email: string; password: string } | { kind: 'magic_link'; token: string };

/**
 * The sign-in sequence every client shares: first factor, then a code only if the backend asks.
 *
 * Web, mobile and the extension differ in how they draw the steps, not in when the second factor
 * is requested, so the reading of totp_required lives here and a client only renders the step.
 * The first factor stays in memory for the retry: the same request carries both, so the server
 * never holds a half-signed-in session.
 */
export function createSignInFlow(user: Pick<UserApi, 'login' | 'verifyMagicLink'>) {
	let step: SignInStep = 'credentials';
	let proof: Proof | null = null;

	function send(secondFactor: SecondFactor | undefined): Promise<void> {
		if (proof === null) throw new Error('no first factor to send');
		if (proof.kind === 'password') {
			return secondFactor === undefined
				? user.login(proof.email, proof.password)
				: user.login(proof.email, proof.password, secondFactor);
		}
		return secondFactor === undefined
			? user.verifyMagicLink(proof.token)
			: user.verifyMagicLink(proof.token, secondFactor);
	}

	async function attempt(next: Proof, secondFactor?: SecondFactor): Promise<SignInOutcome> {
		proof = next;
		try {
			await send(secondFactor);
			step = 'credentials';
			proof = null;
			return 'signed_in';
		} catch (error) {
			const failure = secondFactorFailure(error);
			if (failure !== null) {
				if (step === 'credentials') step = 'code';
				return failure === 'totp_required' ? 'challenge' : 'wrong_code';
			}
			if (step === 'credentials') proof = null;
			return error instanceof ApiError && error.status === 401 ? 'bad_credentials' : 'failed';
		}
	}

	return {
		get step(): SignInStep {
			return step;
		},
		signIn: (email: string, password: string) => attempt({ kind: 'password', email, password }),
		signInWithMagicLink: (token: string) => attempt({ kind: 'magic_link', token }),
		/** Answers the challenge with the authenticator code, or with a recovery code when that is the step shown. */
		submitSecondFactor(value: string): Promise<SignInOutcome> {
			if (proof === null) throw new Error('no sign-in is waiting for a second factor');
			const trimmed = value.trim();
			return attempt(proof, step === 'recovery' ? { recovery_code: trimmed } : { totp_code: trimmed });
		},
		/** A lost phone must not lock the account out: recovery codes are one tap away from the code step. */
		toggleRecovery(): void {
			if (step === 'code') step = 'recovery';
			else if (step === 'recovery') step = 'code';
		}
	};
}

export type SignInFlow = ReturnType<typeof createSignInFlow>;
