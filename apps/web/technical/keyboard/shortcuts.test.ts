import { afterEach, describe, expect, it } from 'vitest';
import { bindShortcuts } from './shortcuts';

let teardown: (() => void) | null = null;

function bind(handlers: Parameters<typeof bindShortcuts>[0]) {
	teardown = bindShortcuts(handlers);
}

/** Dispatched on the document the way a real keypress reaches it, so nothing is stubbed away. */
function press(key: string, init: KeyboardEventInit = {}, target: EventTarget = document) {
	const event = new KeyboardEvent('keydown', { key, bubbles: true, cancelable: true, ...init });
	target.dispatchEvent(event);
	return event;
}

afterEach(() => {
	teardown?.();
	teardown = null;
	document.body.innerHTML = '';
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
