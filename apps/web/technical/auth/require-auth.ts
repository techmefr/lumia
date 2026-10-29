import { base } from '$technical/paths/base';
import { goto } from '$app/navigation';
import { lumia } from '../api/client';

/** Call from a protected page's onMount; redirects to /login when no session exists. */
export function requireAuth(): boolean {
	if (!lumia.user.isAuthenticated()) {
		void goto(base + '/login');
		return false;
	}
	return true;
}
