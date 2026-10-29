export function ownerFromToken(token: string | null): string | null {
	if (!token) return null;
	const payload = token.split('.')[1];
	if (!payload) return null;
	try {
		const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
		const claims = JSON.parse(atob(base64)) as { sub?: unknown };
		return typeof claims.sub === 'string' ? claims.sub : null;
	} catch {
		return null;
	}
}
