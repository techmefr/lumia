export function stripQueryParam(name: string): void {
	const url = new URL(window.location.href);
	if (!url.searchParams.has(name)) return;
	url.searchParams.delete(name);
	window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash);
}
