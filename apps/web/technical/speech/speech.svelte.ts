/**
 * Thin wrapper over the Web Speech API's synthesis side.
 *
 * Two quirks drive the shape of this class. Long utterances are cut off or stall in several
 * browsers, so text is split into sentence-sized chunks and queued one at a time. And
 * `speechSynthesis.pause()` is unreliable on some engines, so pausing cancels the current chunk
 * and resuming re-speaks it from its start rather than mid-word.
 */
import type { MessageKey } from '$technical/i18n/i18n.svelte';

import { BLOCK_SEPARATOR } from './readable-text';

const MAX_CHUNK_LENGTH = 220;

/**
 * `silent` is the engine answering that it finished without ever speaking — no voice for the
 * language, most often. `not-allowed` is a reading the browser refused for want of a gesture it
 * counts as one.
 */
export type SpeechFailure = 'silent' | 'engine' | 'not-allowed';

/** What to tell the reader for each way a reading can come to nothing. */
export const SPEECH_FAILURE_MESSAGES: Record<SpeechFailure, MessageKey> = {
	silent: 'article.speechFailed.silent',
	engine: 'article.speechFailed.engine',
	'not-allowed': 'article.speechFailed.not-allowed'
};

export function splitIntoChunks(text: string): string[] {
	// No chunk may straddle a block boundary: the voice would run two paragraphs together, and the
	// karaoke highlight looks its chunk up inside a single block of the rendered article.
	if (text.includes(BLOCK_SEPARATOR)) {
		return text
			.split(BLOCK_SEPARATOR)
			.flatMap((block) => splitIntoChunks(block))
			.filter(Boolean);
	}
	return chunkOneBlock(text);
}

function chunkOneBlock(text: string): string[] {
	const sentences = text
		.replace(/\s+/g, ' ')
		.trim()
		.split(/(?<=[.!?…])\s+/)
		.filter(Boolean);

	const chunks: string[] = [];
	let current = '';
	for (const sentence of sentences) {
		if (sentence.length > MAX_CHUNK_LENGTH) {
			if (current) {
				chunks.push(current);
				current = '';
			}
			// A single very long sentence still has to be broken, on whitespace, to get spoken.
			for (const piece of sentence.match(new RegExp(`.{1,${MAX_CHUNK_LENGTH}}(\\s|$)`, 'g')) ?? []) {
				chunks.push(piece.trim());
			}
			continue;
		}
		if (`${current} ${sentence}`.trim().length > MAX_CHUNK_LENGTH) {
			chunks.push(current);
			current = sentence;
		} else {
			current = `${current} ${sentence}`.trim();
		}
	}
	if (current) chunks.push(current);
	return chunks;
}

export class SpeechReader {
	speaking = $state(false);
	paused = $state(false);
	/** 0 to 1 across the whole queued text. */
	progress = $state(0);
	/** The chunk being spoken right now, empty when silent. Drives the karaoke highlight. */
	currentChunk = $state('');
	/**
	 * Why the reading stopped short, null when nothing went wrong. Set instead of running the
	 * done callback: a reading that produced no sound must not count as an article read.
	 */
	error = $state<SpeechFailure | null>(null);

	private chunks: string[] = [];
	private index = 0;
	/**
	 * The utterance currently allowed to advance the queue. `cancel()` fires `onend` for the
	 * utterance it drops, and that is the same event the queue advances on — so a cancelled
	 * utterance whose event arrives late would silently skip the chunk that replaced it, or end the
	 * article outright when it was the last one. Only the active utterance counts.
	 */
	private utterance: SpeechSynthesisUtterance | null = null;
	/**
	 * How many chunks the engine actually spoke. An engine that holds no voice for the language
	 * answers every chunk instantly, so this is what tells a stray failure mid-article — worth
	 * skipping over — apart from a reading that never produced a sound.
	 */
	private spokenChunks = 0;
	private onDone: (() => void) | null = null;
	private rate = 1;
	private lang = 'fr-FR';

	get supported(): boolean {
		return typeof window !== 'undefined' && 'speechSynthesis' in window;
	}

	speak(text: string, options: { rate?: number; lang?: string; onDone?: () => void } = {}): void {
		if (!this.supported) return;
		this.stop();

		this.chunks = splitIntoChunks(text);
		this.index = 0;
		this.spokenChunks = 0;
		this.error = null;
		this.rate = options.rate ?? 1;
		this.onDone = options.onDone ?? null;
		this.lang = options.lang ?? 'fr-FR';
		if (this.chunks.length === 0) {
			this.onDone?.();
			return;
		}
		this.speaking = true;
		this.paused = false;
		this.speakCurrent();
	}

	setRate(rate: number): void {
		this.rate = rate;
		// The rate of an utterance already handed to the engine can't be changed; restart the chunk.
		if (this.speaking && !this.paused) {
			this.utterance = null;
			window.speechSynthesis.cancel();
			this.speakCurrent();
		}
	}

	pause(): void {
		if (!this.speaking || this.paused) return;
		this.paused = true;
		window.speechSynthesis.cancel();
	}

	resume(): void {
		if (!this.speaking || !this.paused) return;
		this.paused = false;
		this.speakCurrent();
	}

	stop(): void {
		if (!this.supported) return;
		this.onDone = null;
		this.chunks = [];
		this.index = 0;
		this.speaking = false;
		this.paused = false;
		this.progress = 0;
		this.currentChunk = '';
		this.utterance = null;
		this.spokenChunks = 0;
		window.speechSynthesis.cancel();
	}

	private speakCurrent(): void {
		const chunk = this.chunks[this.index];
		if (chunk === undefined) {
			const done = this.onDone;
			this.stop();
			done?.();
			return;
		}

		this.currentChunk = chunk;
		const utterance = new SpeechSynthesisUtterance(chunk);
		this.utterance = utterance;
		utterance.rate = this.rate;
		utterance.lang = this.lang;
		let started = false;
		utterance.onstart = () => {
			started = true;
			this.spokenChunks += 1;
		};
		utterance.onend = () => {
			// A cancel() from pause()/stop()/setRate() also fires onend; only advance while actually
			// playing, and only for the utterance still on air.
			if (this.paused || !this.speaking || this.utterance !== utterance) return;
			// An utterance that ended without ever starting was never spoken.
			if (!started) {
				this.skipOrGiveUp('silent');
				return;
			}
			this.advance();
		};
		utterance.onerror = (event: SpeechSynthesisErrorEvent) => {
			if (this.paused || !this.speaking || this.utterance !== utterance) return;
			// Our own pause()/stop()/setRate() cancels surface here on some engines. They are not
			// failures, and the utterance they interrupted is re-spoken by whoever cancelled it.
			if (event.error === 'interrupted' || event.error === 'canceled') return;
			this.skipOrGiveUp(event.error === 'not-allowed' ? 'not-allowed' : 'engine');
		};
		window.speechSynthesis.speak(utterance);
	}

	private advance(): void {
		this.index += 1;
		this.progress = this.index / this.chunks.length;
		this.speakCurrent();
	}

	/**
	 * A chunk the engine would not speak. One of those mid-article — a stray character, a hiccup —
	 * is worth stepping over rather than ending the reading. But when nothing has been spoken at
	 * all, the engine is not hiccupping: it has no voice for this language and will answer every
	 * chunk the same way. Stepping over them all would read the article in silence, in one burst,
	 * and then report it finished — which is what marks it read.
	 */
	private skipOrGiveUp(reason: SpeechFailure): void {
		if (this.spokenChunks === 0) {
			this.stop();
			this.error = reason;
			return;
		}
		this.advance();
	}
}
