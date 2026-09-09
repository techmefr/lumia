import { describe, expect, it } from 'vitest';
import { sanitizeArticleHtml } from './sanitize-html';

// Article bodies come from third-party feeds. Everything below is what a hostile or compromised
// source can put in one, so these are the cases that decide whether {@html} is safe.
describe('sanitizeArticleHtml', () => {
	it('keeps the markup an article is actually made of', () => {
		const html = '<p>Un <strong>kiosque</strong> et un <a href="https://blog.test">lien</a>.</p>';
		expect(sanitizeArticleHtml(html)).toBe(html);
	});

	it('strips a script tag', () => {
		expect(sanitizeArticleHtml('<p>ok</p><script>fetch("/steal")</script>')).toBe('<p>ok</p>');
	});

	it('strips an inline event handler', () => {
		expect(sanitizeArticleHtml('<img src="x" onerror="fetch(1)">')).not.toContain('onerror');
	});

	it('strips a javascript: url while keeping the link text', () => {
		const cleaned = sanitizeArticleHtml('<a href="javascript:alert(1)">lire</a>');
		expect(cleaned).not.toContain('javascript:');
		expect(cleaned).toContain('lire');
	});

	it('strips an iframe, which a feed has no business injecting', () => {
		expect(sanitizeArticleHtml('<iframe src="https://evil.test"></iframe>')).toBe('');
	});

	it('strips an svg script payload', () => {
		expect(sanitizeArticleHtml('<svg><script>alert(1)</script></svg>')).not.toContain('alert');
	});

	it('strips a form, so no article can phish a reader', () => {
		const cleaned = sanitizeArticleHtml('<form action="https://evil.test"><input name="p"></form>');
		expect(cleaned).not.toContain('<form');
		expect(cleaned).not.toContain('<input');
	});

	it.each(['button', 'select', 'textarea', 'label'])(
		'strips a %s, which an article body never needs',
		(tag) => {
			expect(sanitizeArticleHtml(`<${tag}>clique ici</${tag}>`)).not.toContain(`<${tag}`);
		}
	);

	it('keeps the text a stripped control was wrapping rather than losing the paragraph', () => {
		expect(sanitizeArticleHtml('<p>avant <button>clique</button> après</p>')).toBe(
			'<p>avant clique après</p>'
		);
	});

	it('leaves an empty string empty', () => {
		expect(sanitizeArticleHtml('')).toBe('');
	});

	it('closes markup the source left open rather than passing it through', () => {
		expect(sanitizeArticleHtml('<p>coupé')).toBe('<p>coupé</p>');
	});
});
