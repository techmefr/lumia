import type { Page } from '@playwright/test';

/**
 * A headless browser ships the Web Speech API but no voice, so `speak()` never fires `onend` and
 * the reader's queue would sit still forever. This replaces the engine — the outer boundary — with
 * one the test drives: it records every utterance in order and only ends one when asked.
 *
 * What stays under test is everything we own: the chunking, the queue advancing one chunk at a
 * time, the button state and the end-of-article signal.
 */
export interface SpeechEngineHandle {
	/** Texts handed to the engine, in the order it received them. */
	spoken: () => Promise<string[]>;
	/** Let the queue run to its end, as a real engine does once it has a voice. */
	playToEnd: () => Promise<void>;
}

export async function installTestSpeechEngine(page: Page): Promise<SpeechEngineHandle> {
	await page.addInitScript(() => {
		const spoken: string[] = [];
		let current: SpeechSynthesisUtterance | null = null;
		let autoEnd = false;

		function endUtterance(utterance: SpeechSynthesisUtterance) {
			if (current !== utterance) return;
			current = null;
			// A real engine announces the start of an utterance it speaks before announcing its end,
			// and the reader treats an utterance that ended without ever starting as one no voice
			// was found for — it stops the reading there rather than marching through the queue in
			// silence. A test engine that skipped `start` would look exactly like that failure.
			utterance.onstart?.(new Event('start') as SpeechSynthesisEvent);
			utterance.onend?.(new Event('end') as SpeechSynthesisEvent);
		}

		class TestUtterance {
			rate = 1;
			lang = '';
			onstart: ((event: Event) => void) | null = null;
			onend: ((event: Event) => void) | null = null;
			onerror: ((event: Event) => void) | null = null;
			constructor(public text: string) {}
		}

		const engine = {
			speak(utterance: SpeechSynthesisUtterance) {
				spoken.push(utterance.text);
				current = utterance;
				// Deferred rather than immediate: the reader queues the next chunk from inside
				// `onend`, and ending synchronously here would recurse through the whole article.
				if (autoEnd) setTimeout(() => endUtterance(utterance), 0);
			},
			cancel() {
				// A real engine fires `onend` for the utterance it drops, which is exactly the case
				// the reader has to tell apart from a natural end.
				const cancelled = current;
				current = null;
				cancelled?.onend?.(new Event('end') as SpeechSynthesisEvent);
			},
			pause() {},
			resume() {},
			getVoices: () => []
		};

		Object.defineProperty(window, 'speechSynthesis', { value: engine, configurable: true });
		Object.defineProperty(window, 'SpeechSynthesisUtterance', {
			value: TestUtterance,
			configurable: true
		});
		Object.defineProperty(window, 'lumiaTestSpeech', {
			value: {
				spoken,
				playToEnd() {
					autoEnd = true;
					if (current) setTimeout(() => endUtterance(current!), 0);
				}
			},
			configurable: true
		});
	});

	return {
		spoken: () =>
			page.evaluate(
				() => (window as unknown as { lumiaTestSpeech: { spoken: string[] } }).lumiaTestSpeech.spoken
			),
		playToEnd: () =>
			page.evaluate(() =>
				(
					window as unknown as { lumiaTestSpeech: { playToEnd: () => void } }
				).lumiaTestSpeech.playToEnd()
			)
	};
}
