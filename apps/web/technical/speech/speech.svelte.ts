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
	/** The chunk being spoken right now, empty when silent. Drives the karaoke highlight. */
	currentChunk = $state('');

	private chunks: string[] = [];
	private index = 0;
	/**
	 * The utterance currently allowed to advance the queue. `cancel()` fires `onend` for the
	 * utterance it drops, and that is the same event the queue advances on — so a cancelled
	 * utterance whose event arrives late would silently skip the chunk that replaced it, or end the
	 * article outright when it was the last one. Only the active utterance counts.
	 */
	private utterance: SpeechSynthesisUtterance | null = null;
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
		utterance.onend = () => {
			// A cancel() from pause()/stop()/setRate() also fires onend; only advance while actually
			// playing, and only for the utterance still on air.
			if (this.paused || !this.speaking || this.utterance !== utterance) return;
			this.index += 1;
			this.progress = this.index / this.chunks.length;
			this.speakCurrent();
		};
		utterance.onerror = () => {
			if (this.paused || !this.speaking || this.utterance !== utterance) return;
			this.index += 1;
			this.speakCurrent();
		};
		window.speechSynthesis.speak(utterance);
	}
}
