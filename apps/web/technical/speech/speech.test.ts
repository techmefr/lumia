import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fakeSpeechSynthesis, type FakeSynthesis } from '../../test-support/fake-speech-synthesis';
import { SpeechReader, splitIntoChunks } from './speech.svelte';

const MAX = 220;

describe('splitIntoChunks', () => {
	it('returns nothing for empty text', () => {
		expect(splitIntoChunks('')).toEqual([]);
	});

	it('returns nothing for whitespace alone', () => {
		expect(splitIntoChunks('   \n\t ')).toEqual([]);
	});

	it('keeps a short paragraph in one piece', () => {
		expect(splitIntoChunks('Un kiosque numérique. Et une une.')).toEqual([
			'Un kiosque numérique. Et une une.'
		]);
	});

	it('collapses the whitespace the html left behind', () => {
		expect(splitIntoChunks('Deux\n\n  mots.')).toEqual(['Deux mots.']);
	});

	it('never exceeds the chunk ceiling the engines choke on', () => {
		const text = Array.from({ length: 40 }, (_, i) => `Phrase numéro ${i} un peu longue.`).join(' ');
		expect(splitIntoChunks(text).every((chunk) => chunk.length <= MAX)).toBe(true);
	});

	it('loses no word, so nothing goes unspoken', () => {
		const text = Array.from({ length: 40 }, (_, i) => `Phrase numéro ${i} un peu longue.`).join(' ');
		const words = (value: string) => value.split(/\s+/).filter(Boolean);
		expect(words(splitIntoChunks(text).join(' '))).toEqual(words(text));
	});

	it('breaks on sentence ends rather than mid-sentence', () => {
		const text = `${'a'.repeat(150)}. ${'b'.repeat(150)}.`;
		const chunks = splitIntoChunks(text);
		expect(chunks).toHaveLength(2);
		expect(chunks.every((chunk) => chunk.endsWith('.'))).toBe(true);
	});

	it.each(['!', '?', '…'])('treats %s as a sentence end too', (mark) => {
		const text = `${'a'.repeat(150)}${mark} ${'b'.repeat(150)}.`;
		expect(splitIntoChunks(text)).toHaveLength(2);
	});

	it('still breaks a single sentence too long to speak in one go', () => {
		const text = `${Array.from({ length: 60 }, () => 'mot').join(' ')}.`;
		const chunks = splitIntoChunks(text);
		expect(chunks.length).toBeGreaterThan(1);
		expect(chunks.every((chunk) => chunk.length <= MAX)).toBe(true);
	});

	it('breaks that long sentence on whitespace, never inside a word', () => {
		const text = `${Array.from({ length: 60 }, () => 'anticonstitutionnellement').join(' ')}.`;
		const chunks = splitIntoChunks(text);
		expect(chunks.every((chunk) => !chunk.startsWith('nellement'))).toBe(true);
		expect(chunks.join(' ')).toContain('anticonstitutionnellement anticonstitutionnellement');
	});

	it('leaves no empty chunk, which would be a silent gap in the reading', () => {
		const text = `Court. ${'a'.repeat(400)}. Court aussi.`;
		expect(splitIntoChunks(text).every((chunk) => chunk.trim().length > 0)).toBe(true);
	});

	it('packs several short sentences together rather than one chunk each', () => {
		const text = 'Un. Deux. Trois. Quatre. Cinq.';
		expect(splitIntoChunks(text)).toHaveLength(1);
	});

	it('handles text with no terminal punctuation at all', () => {
		expect(splitIntoChunks('Un titre sans point')).toEqual(['Un titre sans point']);
	});
});

describe('SpeechReader without an engine', () => {
	// jsdom implements no Web Speech API, which is also the real situation on a browser that has
	// none: the reader has to stay silent and inert rather than throw on the first press of play.
	it('reports itself unsupported', () => {
		expect(new SpeechReader().supported).toBe(false);
	});

	it('does nothing when asked to speak', () => {
		const reader = new SpeechReader();
		reader.speak('Un article.');
		expect(reader.speaking).toBe(false);
		expect(reader.currentChunk).toBe('');
	});

	it('does nothing when asked to stop', () => {
		expect(() => new SpeechReader().stop()).not.toThrow();
	});
});

describe('SpeechReader', () => {
	let engine: FakeSynthesis;

	beforeEach(() => {
		engine = fakeSpeechSynthesis();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	const TWO_CHUNKS = `${'a'.repeat(200)}. ${'b'.repeat(200)}.`;

	it('reports itself supported once the engine is there', () => {
		expect(new SpeechReader().supported).toBe(true);
	});

	it('starts speaking the first chunk straight away', () => {
		const reader = new SpeechReader();
		reader.speak('Un article court.');

		expect(reader.speaking).toBe(true);
		expect(engine.spoken.map((utterance) => utterance.text)).toEqual(['Un article court.']);
		expect(reader.currentChunk).toBe('Un article court.');
	});

	it('speaks at the rate and in the language it was given', () => {
		const reader = new SpeechReader();
		reader.speak('Un article.', { rate: 1.5, lang: 'en-GB' });

		expect(engine.spoken[0].rate).toBe(1.5);
		expect(engine.spoken[0].lang).toBe('en-GB');
	});

	it('reads french at normal speed unless told otherwise', () => {
		const reader = new SpeechReader();
		reader.speak('Un article.');

		expect(engine.spoken[0].rate).toBe(1);
		expect(engine.spoken[0].lang).toBe('fr-FR');
	});

	// The queue is the whole point of the class: engines cut off or stall on a long utterance, so
	// the text goes out one sentence-sized chunk at a time and the next one waits for the last.
	it('queues the chunks rather than handing the engine the whole article', () => {
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS);

		expect(engine.spoken).toHaveLength(1);

		engine.finish();

		expect(engine.spoken).toHaveLength(2);
		expect(reader.currentChunk).toBe(engine.spoken[1].text);
	});

	it('reports progress across the whole text, not across one chunk', () => {
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS);
		expect(reader.progress).toBe(0);

		engine.finish();
		expect(reader.progress).toBe(0.5);
	});

	it('falls silent and reports itself done at the end', () => {
		const done = vi.fn();
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS, { onDone: done });

		engine.finish();
		engine.finish();

		expect(done).toHaveBeenCalledTimes(1);
		expect(reader.speaking).toBe(false);
		expect(reader.currentChunk).toBe('');
		expect(reader.progress).toBe(0);
	});

	// A playlist chains one article into the next off this callback, so an article whose text is
	// empty must still report done or the playlist stops there.
	it('reports done immediately for text with nothing to say', () => {
		const done = vi.fn();
		const reader = new SpeechReader();
		reader.speak('   ', { onDone: done });

		expect(done).toHaveBeenCalledTimes(1);
		expect(reader.speaking).toBe(false);
		expect(engine.spoken).toHaveLength(0);
	});

	it('drops the previous article when asked to speak a new one', () => {
		const first = vi.fn();
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS, { onDone: first });
		reader.speak('Un autre article.');

		expect(first).not.toHaveBeenCalled();
		expect(reader.currentChunk).toBe('Un autre article.');
		expect(engine.spoken[engine.spoken.length - 1].text).toBe('Un autre article.');
	});
});

describe('SpeechReader pausing', () => {
	let engine: FakeSynthesis;

	beforeEach(() => {
		engine = fakeSpeechSynthesis();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	const TWO_CHUNKS = `${'a'.repeat(200)}. ${'b'.repeat(200)}.`;

	// `speechSynthesis.pause()` is unreliable on several engines, so pausing cancels instead. The
	// cancel fires onend, which is exactly what advancing the queue listens to: mistaking one for
	// the other would silently skip a paragraph every time the reader pauses.
	it('does not advance the queue when it pauses', () => {
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS);
		const chunk = reader.currentChunk;

		reader.pause();

		expect(reader.paused).toBe(true);
		expect(reader.speaking).toBe(true);
		expect(reader.currentChunk).toBe(chunk);
		expect(engine.spoken).toHaveLength(1);
	});

	it('re-speaks the paused chunk from its start when it resumes', () => {
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS);
		const chunk = reader.currentChunk;

		reader.pause();
		reader.resume();

		expect(reader.paused).toBe(false);
		expect(engine.spoken.map((utterance) => utterance.text)).toEqual([chunk, chunk]);
	});

	it('carries on to the next chunk after a pause and a resume', () => {
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS);

		reader.pause();
		reader.resume();
		engine.finish();

		expect(reader.progress).toBe(0.5);
		expect(engine.spoken).toHaveLength(3);
	});

	it('ignores a pause when nothing is being read', () => {
		const reader = new SpeechReader();
		reader.pause();
		expect(reader.paused).toBe(false);
	});

	it('ignores a second pause', () => {
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS);
		reader.pause();
		const cancelsAfterFirst = engine.cancels;

		reader.pause();

		expect(engine.cancels).toBe(cancelsAfterFirst);
	});

	it('ignores a resume when it was not paused', () => {
		const reader = new SpeechReader();
		reader.speak(TWO_CHUNKS);

		reader.resume();

		expect(engine.spoken).toHaveLength(1);
	});
});

describe('SpeechReader speed', () => {
	let engine: FakeSynthesis;

	beforeEach(() => {
		engine = fakeSpeechSynthesis();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	// The rate of an utterance already handed to the engine cannot be changed, so the current
	// chunk is restarted at the new speed. Without that, the slider does nothing until the next
	// paragraph.
	it('restarts the current chunk at the new speed', () => {
		const reader = new SpeechReader();
		reader.speak('Un article.');

		reader.setRate(2);

		expect(engine.spoken).toHaveLength(2);
		expect(engine.spoken[1].rate).toBe(2);
		expect(engine.spoken[1].text).toBe('Un article.');
	});

	it('keeps the new speed for the chunks that follow', () => {
		const reader = new SpeechReader();
		reader.speak(`${'a'.repeat(200)}. ${'b'.repeat(200)}.`);

		reader.setRate(0.5);
		engine.finish();

		expect(engine.spoken[engine.spoken.length - 1].rate).toBe(0.5);
	});

	// The engine fires `end` for an utterance it was told to cancel, and that is the same event the
	// queue advances on: changing the speed used to skip the rest of the current chunk, and end a
	// single-chunk article outright — the reader went silent mid-paragraph on a nudge of the slider.
	it('does not end the article when the speed changes', () => {
		const done = vi.fn();
		const reader = new SpeechReader();
		reader.speak('Un article.', { onDone: done });

		reader.setRate(2);

		expect(reader.speaking).toBe(true);
		expect(reader.currentChunk).toBe('Un article.');
		expect(done).not.toHaveBeenCalled();
	});

	it('ignores the cancelled utterance ending after the restart', () => {
		const reader = new SpeechReader();
		reader.speak(`${'a'.repeat(200)}. ${'b'.repeat(200)}.`);
		const cancelled = engine.spoken[0];

		reader.setRate(2);
		cancelled.onend?.();

		expect(reader.progress).toBe(0);
		expect(reader.currentChunk).toBe(cancelled.text);
	});

	it('does not start speaking when the speed changes while paused', () => {
		const reader = new SpeechReader();
		reader.speak('Un article.');
		reader.pause();

		reader.setRate(2);

		expect(engine.spoken).toHaveLength(1);
	});

	it('does not start speaking when the speed changes while silent', () => {
		const reader = new SpeechReader();
		reader.setRate(2);
		expect(engine.spoken).toHaveLength(0);
	});
});

describe('SpeechReader stopping', () => {
	let engine: FakeSynthesis;

	beforeEach(() => {
		engine = fakeSpeechSynthesis();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	it('clears everything it was reading', () => {
		const reader = new SpeechReader();
		reader.speak(`${'a'.repeat(200)}. ${'b'.repeat(200)}.`);
		engine.finish();

		reader.stop();

		expect(reader.speaking).toBe(false);
		expect(reader.paused).toBe(false);
		expect(reader.progress).toBe(0);
		expect(reader.currentChunk).toBe('');
	});

	// Leaving the page mid-article must not chain into the next one.
	it('does not report done when it was stopped', () => {
		const done = vi.fn();
		const reader = new SpeechReader();
		reader.speak('Un article.', { onDone: done });

		reader.stop();

		expect(done).not.toHaveBeenCalled();
	});

	it('speaks nothing more after it was stopped', () => {
		const reader = new SpeechReader();
		reader.speak(`${'a'.repeat(200)}. ${'b'.repeat(200)}.`);

		reader.stop();

		expect(engine.spoken).toHaveLength(1);
	});
});

describe('SpeechReader when the engine fails', () => {
	let engine: FakeSynthesis;

	beforeEach(() => {
		engine = fakeSpeechSynthesis();
	});

	afterEach(() => {
		vi.unstubAllGlobals();
	});

	// One chunk the engine refuses — an unavailable voice, a stray character — must not end the
	// article: it skips to the next rather than stopping the reading dead.
	it('skips the chunk it could not speak and carries on', () => {
		const reader = new SpeechReader();
		reader.speak(`${'a'.repeat(200)}. ${'b'.repeat(200)}.`);

		engine.fail();

		expect(reader.speaking).toBe(true);
		expect(engine.spoken).toHaveLength(2);
	});

	it('reports done when the last chunk is the one that failed', () => {
		const done = vi.fn();
		const reader = new SpeechReader();
		reader.speak('Un article.', { onDone: done });

		engine.fail();

		expect(done).toHaveBeenCalledTimes(1);
		expect(reader.speaking).toBe(false);
	});

	it('ignores a failure that arrives after it was stopped', () => {
		const done = vi.fn();
		const reader = new SpeechReader();
		reader.speak('Un article.', { onDone: done });

		reader.stop();
		engine.fail();

		expect(done).not.toHaveBeenCalled();
		expect(reader.speaking).toBe(false);
	});
});
