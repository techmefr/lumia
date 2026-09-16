import { cleanup, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ErrorPage from './+error.svelte';

let status = 404;
vi.mock('$app/state', () => ({
	page: {
		get status() {
			return status;
		}
	}
}));

function errorPage() {
	const { container } = render(ErrorPage);
	return {
		heading: () => container.querySelector('h1')?.textContent?.trim() ?? '',
		back: () => container.querySelector<HTMLAnchorElement>('a[href$="/articles"]')
	};
}

afterEach(() => {
	cleanup();
});

describe('the error screen', () => {
	// The status alone decides which of the two messages applies: anything other than 404 is a
	// failure, not a page that was never there.
	it('says the page does not exist on a 404', () => {
		status = 404;

		expect(errorPage().heading()).toBe('Page not found');
	});

	it('says something went wrong on any other status', () => {
		status = 500;

		expect(errorPage().heading()).toBe('Something went wrong.');
	});

	it('always offers a way back to the article list', () => {
		status = 500;

		expect(errorPage().back()).not.toBeNull();
	});
});
