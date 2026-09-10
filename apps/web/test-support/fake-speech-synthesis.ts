import { vi } from 'vitest';

interface FakeUtterance {
	text: string;
	rate: number;
	lang: string;
	onstart: (() => void) | null;
	onend: (() => void) | null;
	onerror: ((event: { error: string }) => void) | null;
}

export interface FakeSynthesis {
	/** Every utterance handed to the engine, in order, including re-spoken ones. */
	spoken: FakeUtterance[];
	cancels: number;
	/** What is being spoken right now, or null between utterances. */
	current: () => FakeUtterance | null;
	/**
	 * The engine speaks the current utterance through to its end, announcing its start on the way
	 * as a real one does.
	 */
	finish: () => void;
	/** The engine gives up on the current utterance — an unavailable voice, typically. */
	fail: (error?: string) => void;
	/**
	 * The engine answers `end` without ever having started: no sound came out. That is what a
	 * browser does when it holds no voice for the requested language.
	 */
	finishWithoutSpeaking: () => void;
}

/**
 * jsdom implements no Web Speech API at all, so a reader built on it cannot be exercised without
 * one. This stands in for the engine — the outer boundary — and lets a test say when an utterance
 * starts, ends or fails, which are the events the whole queue advances on.
 */
export function fakeSpeechSynthesis(): FakeSynthesis {
	const spoken: FakeUtterance[] = [];
	let current: FakeUtterance | null = null;
	let cancels = 0;

	class Utterance implements FakeUtterance {
		rate = 1;
		lang = '';
		onstart: (() => void) | null = null;
		onend: (() => void) | null = null;
		onerror: ((event: { error: string }) => void) | null = null;
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
			// A real engine announces the start of an utterance it speaks before announcing its end.
			ending?.onstart?.();
			ending?.onend?.();
		},
		fail(error = 'synthesis-failed') {
			const failing = current;
			current = null;
			failing?.onerror?.({ error });
		},
		finishWithoutSpeaking() {
			const ending = spoken[spoken.length - 1] ?? null;
			current = null;
			ending?.onend?.();
		}
	};
}
