import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { fakeSpeechSynthesis, type FakeSynthesis } from '../../test-support/fake-speech-synthesis';
import { SpeechReader } from './speech.svelte';

class FakeAudio {
	static instances: FakeAudio[] = [];
	static refusePlay = false;
	playbackRate = 1;
	duration = 10;
	currentTime = 0;
	plays = 0;
	pauses = 0;
	onended: (() => void) | null = null;
	onerror: (() => void) | null = null;
	ontimeupdate: (() => void) | null = null;
	constructor(public src: string) {
		FakeAudio.instances.push(this);
	}
	play() {
		this.plays += 1;
		return FakeAudio.refusePlay ? Promise.reject(new Error('NotAllowedError')) : Promise.resolve();
	}
	pause() {
		this.pauses += 1;
	}
}

let synthesis: FakeSynthesis;
const revoked: string[] = [];

beforeEach(() => {
	synthesis = fakeSpeechSynthesis();
	FakeAudio.instances = [];
	FakeAudio.refusePlay = false;
	revoked.length = 0;
	vi.stubGlobal('Audio', FakeAudio);
	URL.createObjectURL = () => 'blob:recording';
	URL.revokeObjectURL = (url: string) => void revoked.push(url);
});

afterEach(() => vi.unstubAllGlobals());

const recording = () => Promise.resolve(new Blob(['mp3'], { type: 'audio/mpeg' }));
const settle = () => vi.waitFor(() => expect(FakeAudio.instances.length).toBeGreaterThan(0));

describe('SpeechReader with a provider recording', () => {
	it('plays the recording and never touches the browser voice', async () => {
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: recording, rate: 1.5 });
		await settle();

		expect(FakeAudio.instances[0].plays).toBe(1);
		expect(FakeAudio.instances[0].playbackRate).toBe(1.5);
		expect(synthesis.spoken).toHaveLength(0);
		expect(reader.speaking).toBe(true);
	});

	it('runs the done callback when the recording ends, then frees it', async () => {
		const onDone = vi.fn();
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: recording, onDone });
		await settle();

		FakeAudio.instances[0].onended?.();

		expect(onDone).toHaveBeenCalledOnce();
		expect(reader.speaking).toBe(false);
		expect(revoked).toEqual(['blob:recording']);
	});

	it('follows the playback position as progress', async () => {
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: recording });
		await settle();

		FakeAudio.instances[0].currentTime = 4;
		FakeAudio.instances[0].ontimeupdate?.();

		expect(reader.progress).toBe(0.4);
	});

	it('pauses, resumes and changes speed on the recording itself', async () => {
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: recording });
		await settle();
		const audio = FakeAudio.instances[0];

		reader.pause();
		expect(audio.pauses).toBeGreaterThan(0);
		expect(reader.paused).toBe(true);
		reader.resume();
		expect(audio.plays).toBe(2);
		reader.setRate(2);
		expect(audio.playbackRate).toBe(2);
		expect(synthesis.spoken).toHaveLength(0);
	});

	it.each([
		['has nothing', () => Promise.resolve(null)],
		['fails', () => Promise.reject(new Error('502'))]
	])('falls back on the browser voice when the provider %s', async (_name, audio) => {
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio });

		await vi.waitFor(() => expect(synthesis.spoken).toHaveLength(1));
		expect(synthesis.spoken[0].text).toBe('Bonjour.');
	});

	it('falls back on the browser voice when the browser refuses to play the recording', async () => {
		FakeAudio.refusePlay = true;
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: recording });

		await vi.waitFor(() => expect(synthesis.spoken).toHaveLength(1));
		expect(revoked).toEqual(['blob:recording']);
	});

	it('does not start a recording that arrived after the reader stopped', async () => {
		let release: (blob: Blob) => void = () => undefined;
		const late = () => new Promise<Blob | null>((resolve) => (release = resolve));
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: late });
		reader.stop();
		release(new Blob(['mp3']));
		await Promise.resolve();
		await Promise.resolve();

		expect(FakeAudio.instances).toHaveLength(0);
		expect(synthesis.spoken).toHaveLength(0);
	});

	it('stays silent while paused during the download, then speaks on resume', async () => {
		let release: (blob: Blob | null) => void = () => undefined;
		const late = () => new Promise<Blob | null>((resolve) => (release = resolve));
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: late });
		reader.pause();
		release(null);
		await Promise.resolve();
		await Promise.resolve();
		expect(synthesis.spoken).toHaveLength(0);

		reader.resume();
		expect(synthesis.spoken).toHaveLength(1);
	});

	it('reports an engine failure when the recording errors mid-playback', async () => {
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: recording });
		await settle();

		FakeAudio.instances[0].onerror?.();

		expect(reader.error).toBe('engine');
		expect(reader.speaking).toBe(false);
	});
});

describe('seeking inside a provider recording', () => {
	it('moves the recording itself rather than starting the browser voice', async () => {
		const reader = new SpeechReader();
		reader.speak('Bonjour.', { audio: recording });
		await settle();
		const audio = FakeAudio.instances[0];

		reader.seek(0.5);

		expect(audio.currentTime).toBe(5);
		expect(reader.progress).toBe(0.5);
		expect(synthesis.spoken).toHaveLength(0);
	});
});
