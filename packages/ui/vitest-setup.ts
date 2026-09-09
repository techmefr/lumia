import '@testing-library/jest-dom/vitest';

// jsdom implements no animation api, and svelte drives every `transition:` through
// `element.animate`. Without this, mounting anything that animates throws from inside the
// framework — an error unrelated to the behaviour under test, and one that hides real failures.
// A browser api at the outer boundary is the one thing worth stubbing here.
if (typeof Element !== 'undefined' && !Element.prototype.animate) {
	Element.prototype.animate = function animate(): Animation {
		const animation = {
			currentTime: 0,
			playState: 'finished',
			startTime: 0,
			effect: null,
			finished: Promise.resolve(),
			cancel() {},
			finish() {},
			pause() {},
			play() {},
			reverse() {},
			addEventListener() {},
			removeEventListener() {}
		};
		return animation as unknown as Animation;
	} as Element['animate'];
}
