/**
 * The browser's online/offline signal, as reactive state. `navigator.onLine` alone is only "has a
 * link-layer connection", not "the API answers" — good enough here, since the app's own fetches
 * already fail closed and fall back to the offline copy when the network genuinely is not there.
 */
let online = $state(typeof navigator === 'undefined' ? true : navigator.onLine);

export function isOnline(): boolean {
	return online;
}

/** Starts listening. Returns a teardown, so the caller (the root layout) owns the lifetime. */
export function watchConnectivity(): () => void {
	if (typeof window === 'undefined') return () => {};

	function goOnline() {
		online = true;
	}
	function goOffline() {
		online = false;
	}

	window.addEventListener('online', goOnline);
	window.addEventListener('offline', goOffline);
	return () => {
		window.removeEventListener('online', goOnline);
		window.removeEventListener('offline', goOffline);
	};
}
