function readOnline(): boolean {
	return typeof navigator === 'undefined' ? true : navigator.onLine;
}

class Connectivity {
	online = $state(readOnline());
}

export const connectivity = new Connectivity();

export function watchConnectivity(onReconnect: () => void): () => void {
	function goOnline() {
		connectivity.online = true;
		onReconnect();
	}
	function goOffline() {
		connectivity.online = false;
	}
	connectivity.online = readOnline();
	window.addEventListener('online', goOnline);
	window.addEventListener('offline', goOffline);
	return () => {
		window.removeEventListener('online', goOnline);
		window.removeEventListener('offline', goOffline);
	};
}
