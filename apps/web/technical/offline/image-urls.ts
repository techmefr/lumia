import type { ArticleDetail } from '@lumia/core';

const IMAGE_SOURCE = /<img\b[^>]*?\bsrc\s*=\s*["']([^"']+)["']/gi;

function isRemoteImage(url: string): boolean {
	return /^https?:\/\//i.test(url);
}

export function articleImageUrls(article: ArticleDetail): string[] {
	const urls = new Set<string>();
	if (article.image_url && isRemoteImage(article.image_url)) urls.add(article.image_url);
	for (const match of article.content.matchAll(IMAGE_SOURCE)) {
		if (isRemoteImage(match[1])) urls.add(match[1]);
	}
	return [...urls];
}
