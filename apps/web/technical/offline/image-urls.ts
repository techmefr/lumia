import type { ArticleDetail } from '@lumia/core';

const IMAGE_SOURCE = /<img\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']/gi;

const NAMED_ENTITIES: Record<string, string> = { amp: '&', quot: '"', apos: "'", lt: '<', gt: '>' };

function decodeEntities(value: string): string {
	return value.replace(
		/&(?:#(\d+)|#x([0-9a-f]+)|(amp|quot|apos|lt|gt));/gi,
		(_match, decimal, hexadecimal, named) => {
			if (decimal) return String.fromCodePoint(Number(decimal));
			if (hexadecimal) return String.fromCodePoint(parseInt(hexadecimal, 16));
			return NAMED_ENTITIES[named.toLowerCase()];
		}
	);
}

function isRemoteImage(url: string): boolean {
	return /^https?:\/\//i.test(url);
}

export function articleImageUrls(article: ArticleDetail): string[] {
	const urls = new Set<string>();
	if (article.image_url && isRemoteImage(article.image_url)) urls.add(article.image_url);
	for (const match of article.content.matchAll(IMAGE_SOURCE)) {
		const decoded = decodeEntities(match[1]);
		if (isRemoteImage(decoded)) urls.add(decoded);
	}
	return [...urls];
}
