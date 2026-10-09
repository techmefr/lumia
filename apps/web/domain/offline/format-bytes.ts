const UNITS = ['B', 'KB', 'MB', 'GB'];

/** Human-readable size for the storage indicator. Text-only offline copies rarely clear a few MB,
 *  but the unit still has to follow the number rather than being fixed to one guess. */
export function formatBytes(bytes: number): string {
	if (bytes <= 0) return '0 B';
	const exponent = Math.min(Math.floor(Math.log2(bytes) / 10), UNITS.length - 1);
	const value = bytes / 2 ** (exponent * 10);
	const decimals = exponent === 0 ? 0 : 1;
	return `${value.toFixed(decimals)} ${UNITS[exponent]}`;
}
