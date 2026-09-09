import { vi } from 'vitest';

interface FakeUtterance {
	text: string;
	rate: number;
	lang: string;
	onend: (() => void) | null;
	onerror: (() => void) | null;
}

export interface FakeSynthesis {
	/** Every utterance handed to the engine, in order, including re-spoken ones. */
	spoken: FakeUtterance[];
	cancels: number;
	/** What is being spoken right now, or null between utterances. */
	current: () => FakeUtterance | null;
	/** The engine finishes the current utterance, as a real one does when it reaches the end. */
	finish: () => void;
	/** The engine gives up on the current utterance — an unavailable voice, typically. */
	fail: () => void;
}

/**
 * jsdom implements no Web Speech API at all, so a reader built on it cannot be exercised without
 * one. This stands in for the engine — the outer boundary — and lets a test say when an utterance
 * ends, which is the event the whole queue advances on.
 */
export function fakeSpeechSynthesis(): FakeSynthesis {
	const spoken: FakeUtterance[] = [];
	let current: FakeUtterance | null = null;
	let cancels = 0;

	class Utterance implements FakeUtterance {
		rate = 1;
		lang = '';
		onend: (() => void) | null = null;
		onerror: (() => void) | null = null;
		constructor(public text: string) {}
	}

	vi.stubGlobal('SpeechSynthesisUtterance', Utterance);
	vi.stubGlobal('speechSynthesis', {
		speak(utterance: FakeUtterance) {
			spoken.push(utterance);
			current = utterance;
		},
		cancel() {
			cancels += 1;
			// A real engine fires onend for the utterance it just cancelled, which is exactly the
			// case the reader has to tell apart from a natural end.
			const cancelled = current;
			current = null;
			cancelled?.onend?.();
		}
	});

	return {
		spoken,
		get cancels() {
			return cancels;
		},
		current: () => current,
		finish() {
			const ending = current;
			current = null;
			ending?.onend?.();
		},
		fail() {
			const failing = current;
			current = null;
			failing?.onerror?.();
		}
	};
}
