import { describe, expect, it } from 'vitest';
import { articleDetail } from '../../src/routes/test-support/fixtures';
import { articleImageUrls } from './image-urls';

describe('articleImageUrls', () => {
	it('returns the cover and every remote image of the body, once each', () => {
		const article = articleDetail('a1', {
			image_url: 'https://img.test/cover.jpg',
			content:
				'<img src="https://img.test/cover.jpg"><p><img alt="x" src=\'http://img.test/b.png\'></p>'
		});

		expect(articleImageUrls(article)).toEqual(['https://img.test/cover.jpg', 'http://img.test/b.png']);
	});

	it('ignores relative paths and inline data, which a cache keyed by address cannot serve', () => {
		const article = articleDetail('a1', {
			image_url: null,
			content: '<img src="/local.png"><img src="data:image/png;base64,AAAA">'
		});

		expect(articleImageUrls(article)).toEqual([]);
	});

	it('finds nothing in a body without pictures', () => {
		expect(articleImageUrls(articleDetail('a1'))).toEqual([]);
	});
});
