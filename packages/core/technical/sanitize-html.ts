import DOMPurify from 'dompurify';

/**
 * Article content originates from third-party RSS sources (via Miniflux) — a compromised or
 * malicious feed can embed script/event-handler payloads, so it is untrusted HTML and must be
 * sanitized before ever reaching innerHTML/{@html}.
 */
/**
 * Form controls are on DOMPurify's default allow-list, which is right for a rich-text editor and
 * wrong here: an article body has no legitimate use for one, while a hostile feed can render a
 * credible login form inside the reader's own trusted interface and post it anywhere it likes.
 */
const FORBIDDEN_TAGS = ['form', 'input', 'button', 'select', 'textarea', 'option', 'label'];

export function sanitizeArticleHtml(html: string): string {
	return DOMPurify.sanitize(html, { FORBID_TAGS: FORBIDDEN_TAGS });
}

/**
 * The text-only variant an offline copy is stored as. Images are the bulk of an article's weight
 * and the one thing a phone cannot fetch again once it has no signal, so a reader who opts an
 * article into offline reading gets its words, not a page of broken image placeholders.
 */
export function sanitizeArticleHtmlForOffline(html: string): string {
	return DOMPurify.sanitize(html, { FORBID_TAGS: [...FORBIDDEN_TAGS, 'img', 'picture', 'source'] });
}
