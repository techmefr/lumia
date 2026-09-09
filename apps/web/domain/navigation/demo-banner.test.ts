import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import DemoBanner from './demo-banner.svelte';

const resetDemo = vi.hoisted(() => vi.fn());
vi.mock('$technical/api/demo/demo-client', () => ({ resetDemo }));

// jsdom refuses to actually navigate and logs a "not implemented" error for a real assignment to
// `window.location.href`; stubbing the property is the outer boundary here, not the reset button.
function stubLocation() {
	const original = window.location;
	const href = { current: original.href };
	Object.defineProperty(window, 'location', {
		configurable: true,
		value: {
			...original,
			get href() {
				return href.current;
			},
			set href(value: string) {
				href.current = value;
			}
		}
	});
	return {
		current: () => href.current,
		restore: () => Object.defineProperty(window, 'location', { configurable: true, value: original })
	};
}

afterEach(() => {
	resetDemo.mockClear();
});

describe('the demo banner', () => {
	it('clears the seeded state and returns to the article list', async () => {
		const location = stubLocation();
		const { container } = render(DemoBanner);

		await fireEvent.click(container.querySelector('[data-test-demo-reset]')!);

		expect(resetDemo).toHaveBeenCalledOnce();
		expect(location.current()).toBe('/articles');
		location.restore();
	});

	it('links to the source repository', () => {
		const { container } = render(DemoBanner);

		const link = container.querySelector<HTMLAnchorElement>('[data-test-demo-code]')!;
		expect(link.href).toBe('https://github.com/techmefr/lumia');
	});
});
