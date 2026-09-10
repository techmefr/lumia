import { afterEach, describe, expect, it, vi } from 'vitest';
import { COMPACT_VIEWPORT_QUERY, MULTI_COLUMN_MIN_PX, watchCompactViewport } from './breakpoints';

interface FakeQuery {
	matches: boolean;
	addEventListener: (type: string, handler: () => void) => void;
	removeEventListener: (type: string, handler: () => void) => void;
}

function stubMatchMedia(matches: boolean) {
	const handlers = new Set<() => void>();
	const query: FakeQuery = {
		matches,
		addEventListener: (_type, handler) => handlers.add(handler),
		removeEventListener: (_type, handler) => handlers.delete(handler)
	};
	const matchMedia = vi.fn(() => query);
	vi.stubGlobal('matchMedia', matchMedia);
	return {
		matchMedia,
		cross(next: boolean) {
			query.matches = next;
			for (const handler of handlers) handler();
		},
		listenerCount: () => handlers.size
	};
}

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('watching the compact viewport', () => {
	it('asks for the width the grid stops being multi-column at', () => {
		const media = stubMatchMedia(false);

		watchCompactViewport(() => {});

		expect(media.matchMedia).toHaveBeenCalledWith(COMPACT_VIEWPORT_QUERY);
		expect(COMPACT_VIEWPORT_QUERY).toContain(String(MULTI_COLUMN_MIN_PX - 1));
	});

	it('reports the current width immediately, without waiting for a resize', () => {
		stubMatchMedia(true);
		const seen: boolean[] = [];

		watchCompactViewport((compact) => seen.push(compact));

		expect(seen).toEqual([true]);
	});

	it('reports every crossing of the threshold', () => {
		const media = stubMatchMedia(false);
		const seen: boolean[] = [];

		watchCompactViewport((compact) => seen.push(compact));
		media.cross(true);
		media.cross(false);

		expect(seen).toEqual([false, true, false]);
	});

	it('stops reporting once released', () => {
		const media = stubMatchMedia(false);
		const seen: boolean[] = [];

		const stop = watchCompactViewport((compact) => seen.push(compact));
		stop();
		media.cross(true);

		expect(seen).toEqual([false]);
		expect(media.listenerCount()).toBe(0);
	});

	// The static build renders these pages without a window, and a mobile-only fallback there would
	// hide the mode selector from every desktop reader until the first resize.
	it('assumes the wide layout when there is no media query support', () => {
		vi.stubGlobal('matchMedia', undefined);
		const seen: boolean[] = [];

		const stop = watchCompactViewport((compact) => seen.push(compact));

		expect(seen).toEqual([false]);
		expect(stop).not.toThrow();
	});
});
