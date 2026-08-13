import DOMPurify from 'dompurify';

/**
 * Article content originates from third-party RSS sources (via Miniflux) — a compromised or
 * malicious feed can embed script/event-handler payloads, so it is untrusted HTML and must be
 * sanitized before ever reaching innerHTML/{@html}.
 */
export function sanitizeArticleHtml(html: string): string {
	return DOMPurify.sanitize(html);
}
