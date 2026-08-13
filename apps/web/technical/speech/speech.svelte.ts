/**
 * Thin wrapper over the Web Speech API's synthesis side.
 *
 * Two quirks drive the shape of this class. Long utterances are cut off or stall in several
 * browsers, so text is split into sentence-sized chunks and queued one at a time. And
 * `speechSynthesis.pause()` is unreliable on some engines, so pausing cancels the current chunk
 * and resuming re-speaks it from its start rather than mid-word.
 */
const MAX_CHUNK_LENGTH = 220;

export function splitIntoChunks(text: string): string[] {
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

	private chunks: string[] = [];
	private index = 0;
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

		const utterance = new SpeechSynthesisUtterance(chunk);
		utterance.rate = this.rate;
		utterance.lang = this.lang;
		utterance.onend = () => {
			// A cancel() from pause()/stop() also fires onend; only advance while actually playing.
			if (this.paused || !this.speaking) return;
			this.index += 1;
			this.progress = this.index / this.chunks.length;
			this.speakCurrent();
		};
		utterance.onerror = () => {
			if (this.paused || !this.speaking) return;
			this.index += 1;
			this.speakCurrent();
		};
		window.speechSynthesis.speak(utterance);
	}
}
