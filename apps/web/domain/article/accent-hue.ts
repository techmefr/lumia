// Curated hue set avoiding adjacent red/green confusion pairs (protanopia/deuteranopia-safe):
// blue, amber, teal, violet, magenta, sky, rust, indigo.
const SAFE_HUES = [220, 35, 175, 265, 320, 200, 15, 245];

/** Deterministic colorblind-safe hue from a feed id, so each source keeps a stable cover color. */
export function accentHueForFeed(feedId: string): number {
	let hash = 0;
	for (let i = 0; i < feedId.length; i++) {
		hash = (hash * 31 + feedId.charCodeAt(i)) >>> 0;
	}
	return SAFE_HUES[hash % SAFE_HUES.length];
}
