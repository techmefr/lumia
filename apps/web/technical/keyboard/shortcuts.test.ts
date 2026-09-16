import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { bindSequenceShortcuts, bindShortcuts } from './shortcuts';
import { setShortcutsEnabled } from './shortcuts-store.svelte';

let teardown: (() => void) | null = null;

function bind(handlers: Parameters<typeof bindShortcuts>[0]) {
	teardown = bindShortcuts(handlers);
}

function bindSequence(prefix: string, handlers: Parameters<typeof bindShortcuts>[0]) {
	teardown = bindSequenceShortcuts(prefix, handlers);
}

/** Dispatched on the document the way a real keypress reaches it, so nothing is stubbed away. */
function press(key: string, init: KeyboardEventInit = {}, target: EventTarget = document) {
	const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
	target.dispatchEvent(event);
	return event;
}

beforeEach(() => {
	setShortcutsEnabled(true);
});

afterEach(() => {
	teardown?.();
	teardown = null;
	document.body.innerHTML = '';
	setShortcutsEnabled(true);
});

describe('bindShortcuts', () => {
	it('runs the handler bound to the key', () => {
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('j');
		expect(seen).toEqual(['next']);
	});

	it('matches the key case-insensitively, so caps lock does not disable the app', () => {
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('J');
		expect(seen).toEqual(['next']);
	});

	it('prevents the default action of a key it handles', () => {
		bind({ '/': () => {} });
		expect(press('/').defaultPrevented).toBe(true);
	});

	it('leaves a key it does not handle to the browser', () => {
		bind({ j: () => {} });
		expect(press('q').defaultPrevented).toBe(false);
	});

	it.each(['metaKey', 'ctrlKey', 'altKey'] as const)(
		'ignores the key when %s is held, so browser shortcuts keep working',
		(modifier) => {
			const seen: string[] = [];
			bind({ r: () => seen.push('reload-ours') });
			press('r', { [modifier]: true });
			expect(seen).toEqual([]);
		}
	);

	it.each(['INPUT', 'TEXTAREA', 'SELECT'])('ignores keys typed inside a %s', (tag) => {
		const field = document.createElement(tag.toLowerCase());
		document.body.append(field);
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('j', {}, field);
		expect(seen).toEqual([]);
	});

	it('ignores keys typed inside a contenteditable element', () => {
		document.body.innerHTML = '<div contenteditable="true" id="editor"></div>';
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('j', {}, document.querySelector('#editor')!);
		expect(seen).toEqual([]);
	});

	it('ignores keys typed in a child of a contenteditable region', () => {
		document.body.innerHTML = '<div contenteditable="true"><b id="inner">gras</b></div>';
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('j', {}, document.querySelector('#inner')!);
		expect(seen).toEqual([]);
	});

	it('still handles keys pressed on a plain element', () => {
		const article = document.createElement('article');
		document.body.append(article);
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('j', {}, article);
		expect(seen).toEqual(['next']);
	});

	it('stops listening once torn down, so a left page keeps no grip on the keyboard', () => {
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		teardown?.();
		teardown = null;
		press('j');
		expect(seen).toEqual([]);
	});
});

describe('the off switch', () => {
	it('stops every shortcut once the reader turns them off', () => {
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		setShortcutsEnabled(false);
		press('j');
		expect(seen).toEqual([]);
	});

	it('leaves the key to the browser while shortcuts are off', () => {
		bind({ '/': () => {} });
		setShortcutsEnabled(false);
		expect(press('/').defaultPrevented).toBe(false);
	});

	it('brings the shortcuts back when they are turned on again', () => {
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		setShortcutsEnabled(false);
		press('j');
		setShortcutsEnabled(true);
		press('j');
		expect(seen).toEqual(['next']);
	});

	it('remembers the choice, so it survives a reload', () => {
		setShortcutsEnabled(false);
		expect(localStorage.getItem('lumia-shortcuts')).toBe('off');
	});
});

describe('overlay handling', () => {
	it.each(['dialog', 'menu'])('ignores keys while a %s is open', (role) => {
		document.body.innerHTML = `<div role="${role}"></div>`;
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('j');
		expect(seen).toEqual([]);
	});

	it('answers again once the overlay is gone', () => {
		document.body.innerHTML = '<div role="dialog"></div>';
		const seen: string[] = [];
		bind({ j: () => seen.push('next') });
		press('j');
		document.body.innerHTML = '';
		press('j');
		expect(seen).toEqual(['next']);
	});
});

describe('bindSequenceShortcuts', () => {
	it('runs the handler when the prefix is followed by its key', () => {
		const seen: string[] = [];
		bindSequence('g', { a: () => seen.push('articles') });
		press('g');
		press('a');
		expect(seen).toEqual(['articles']);
	});

	it('does nothing on the key alone, so it never steals a reading shortcut', () => {
		const seen: string[] = [];
		bindSequence('g', { a: () => seen.push('articles') });
		expect(press('a').defaultPrevented).toBe(false);
		expect(seen).toEqual([]);
	});

	it('disarms after an unknown second key', () => {
		const seen: string[] = [];
		bindSequence('g', { a: () => seen.push('articles') });
		press('g');
		press('q');
		press('a');
		expect(seen).toEqual([]);
	});

	it('disarms once the sequence times out', () => {
		vi.useFakeTimers();
		try {
			const seen: string[] = [];
			bindSequence('g', { a: () => seen.push('articles') });
			press('g');
			vi.advanceTimersByTime(2000);
			press('a');
			expect(seen).toEqual([]);
		} finally {
			vi.useRealTimers();
		}
	});

	it.each(['INPUT', 'TEXTAREA'])('ignores the prefix typed inside a %s', (tag) => {
		const field = document.createElement(tag.toLowerCase());
		document.body.append(field);
		const seen: string[] = [];
		bindSequence('g', { a: () => seen.push('articles') });
		press('g', {}, field);
		press('a', {}, field);
		expect(seen).toEqual([]);
	});

	it('ignores the second key when it is typed into a field', () => {
		document.body.innerHTML = '<input id="search" />';
		const seen: string[] = [];
		bindSequence('g', { a: () => seen.push('articles') });
		press('g');
		press('a', {}, document.querySelector('#search')!);
		expect(seen).toEqual([]);
	});

	it('stays silent while the shortcuts are turned off', () => {
		const seen: string[] = [];
		bindSequence('g', { a: () => seen.push('articles') });
		setShortcutsEnabled(false);
		press('g');
		press('a');
		expect(seen).toEqual([]);
	});

	it('stops listening once torn down', () => {
		const seen: string[] = [];
		bindSequence('g', { a: () => seen.push('articles') });
		teardown?.();
		teardown = null;
		press('g');
		press('a');
		expect(seen).toEqual([]);
	});
});

describe('shifted shortcuts', () => {
	it('prefers the shifted handler when shift is held', () => {
		const seen: string[] = [];
		bind({ j: () => seen.push('move'), 'shift+j': () => seen.push('extend') });
		press('J', { shiftKey: true });
		expect(seen).toEqual(['extend']);
	});

	it('leaves the unshifted handler alone when shift is not held', () => {
		const seen: string[] = [];
		bind({ j: () => seen.push('move'), 'shift+j': () => seen.push('extend') });
		press('j');
		expect(seen).toEqual(['move']);
	});

	// `/` and `?` need shift on most layouts, so a shifted press still falls back to the plain
	// entry rather than being swallowed.
	it('falls back to the plain handler when there is no shifted one', () => {
		const seen: string[] = [];
		bind({ '/': () => seen.push('search') });
		press('/', { shiftKey: true });
		expect(seen).toEqual(['search']);
	});
});
