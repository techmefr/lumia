export function safeHttpHref(value: string | null | undefined): string | undefined {
	if (!value) return undefined;
	try {
		const { protocol } = new URL(value);
		return protocol === 'http:' || protocol === 'https:' ? value : undefined;
	} catch {
		return undefined;
	}
}
