import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { fakeSpeechSynthesis, type FakeSynthesis } from '../../test-support/fake-speech-synthesis';
import { articleDetail, articleSummary } from '../../src/routes/test-support/fixtures';
import { AudioPlayer, RESUME_STORAGE_KEY } from './audio-player.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: {
		article: { getArticle: vi.fn() },
		recommendation: { sendFeedback: vi.fn() }
	}
}));

const api = vi.mocked(lumia, { deep: true });

let engine: FakeSynthesis;

const A = articleSummary('a', { title: 'Premier' });
const B = articleSummary('b', { title: 'Second' });

async function started(articles = [A, B], startIndex = 0) {
	const player = new AudioPlayer();
	await player.play(articles, startIndex);
	return player;
}

function spokenText() {
	return engine.spoken.map((utterance) => utterance.text).join(' ');
}

beforeEach(() => {
	engine = fakeSpeechSynthesis();
	localStorage.clear();
	api.article.getArticle.mockImplementation(async (id: string) =>
		articleDetail(id, { content: `<p>Corps ${id}.</p>` })
	);
	api.recommendation.sendFeedback.mockResolvedValue(undefined);
});

afterEach(() => {
	vi.unstubAllGlobals();
	vi.clearAllMocks();
});

describe('playing a queue', () => {
	it('reads the title then the fetched body', async () => {
		const player = await started();

		expect(player.current?.id).toBe('a');
		expect(player.playing).toBe(true);
		expect(spokenText()).toContain('Premier');
		expect(spokenText()).toContain('Corps a.');
	});

	it('falls back on the summary when the body cannot be fetched', async () => {
		api.article.getArticle.mockRejectedValue(new Error('offline'));
		await started([articleSummary('a', { summary: 'Un résumé court.' })]);

		expect(spokenText()).toContain('Un résumé court.');
	});

	it('chains to the next article and marks the finished one read', async () => {
		const player = await started();

		while (engine.current() && player.current?.id === 'a') engine.finish();

		await vi.waitFor(() => expect(player.current?.id).toBe('b'));
		expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('a', { read: true });
		await vi.waitFor(() => expect(spokenText()).toContain('Corps b.'));
	});

	it('empties itself once the queue runs out', async () => {
		const player = await started([A]);

		while (engine.current()) engine.finish();

		await vi.waitFor(() => expect(player.current).toBeNull());
		expect(player.queue).toEqual([]);
	});

	it('starts where asked inside the queue', async () => {
		const player = await started([A, B], 1);

		expect(player.current?.id).toBe('b');
		expect(player.hasPrevious).toBe(true);
		expect(player.hasNext).toBe(false);
	});
});

describe('controls', () => {
	it('pauses and resumes', async () => {
		const player = await started();

		player.toggle();
		expect(player.paused).toBe(true);
		expect(player.playing).toBe(false);

		player.toggle();
		expect(player.playing).toBe(true);
	});

	it('skips to the next and back to the previous article', async () => {
		const player = await started();

		await player.next();
		expect(player.current?.id).toBe('b');

		await player.previous();
		expect(player.current?.id).toBe('a');
	});

	it('does not go before the first article', async () => {
		const player = await started();

		await player.previous();

		expect(player.current?.id).toBe('a');
	});

	it('re-speaks the current chunk at the new speed', async () => {
		const player = await started();

		player.setRate(1.5);

		expect(player.rate).toBe(1.5);
		expect(engine.spoken[engine.spoken.length - 1].rate).toBe(1.5);
	});

	it('closing silences the player and forgets the queue', async () => {
		const player = await started();

		player.close();

		expect(player.current).toBeNull();
		expect(player.playing).toBe(false);
		expect(engine.current()).toBeNull();
	});

	it('ignores a body that arrives after the article was skipped', async () => {
		let release: (value: ReturnType<typeof articleDetail>) => void = () => {};
		api.article.getArticle.mockImplementationOnce(
			() => new Promise((resolve) => (release = resolve))
		);
		const player = new AudioPlayer();
		const slow = player.play([A, B], 0);

		await player.next();
		release(articleDetail('a', { content: '<p>Retard.</p>' }));
		await slow;

		expect(spokenText()).not.toContain('Retard.');
		expect(player.current?.id).toBe('b');
	});
});

describe('the queue', () => {
	it('starts playing an article enqueued into an empty player', async () => {
		const player = new AudioPlayer();

		await player.enqueue(A);

		expect(player.current?.id).toBe('a');
		expect(player.playing).toBe(true);
	});

	it('appends without interrupting what plays', async () => {
		const player = await started([A]);

		await player.enqueue(B);

		expect(player.current?.id).toBe('a');
		expect(player.queue.map((article) => article.id)).toEqual(['a', 'b']);
	});

	it('does not queue the same article twice', async () => {
		const player = await started([A]);

		await player.enqueue(A);

		expect(player.queue).toHaveLength(1);
	});
});

describe('seeking and resuming', () => {
	const LONG = `<p>${Array.from({ length: 30 }, (_, i) => `Phrase ${i} un peu longue pour faire un morceau. `.repeat(6)).join('</p><p>')}</p>`;

	beforeEach(() => {
		api.article.getArticle.mockResolvedValue(articleDetail('a', { content: LONG }));
	});

	it('jumps to the asked fraction of the article', async () => {
		const player = await started([A]);

		player.seek(0.5);

		expect(player.progress).toBeGreaterThan(0.4);
		expect(player.progress).toBeLessThan(0.6);
	});

	it('steps forward and backward by a few percent', async () => {
		const player = await started([A]);
		player.seek(0.5);
		const middle = player.progress;

		player.skipForward();
		expect(player.progress).toBeGreaterThan(middle);

		player.skipBackward();
		player.skipBackward();
		expect(player.progress).toBeLessThan(middle);
	});

	it('remembers where the reading got to', async () => {
		const player = await started([A]);

		player.seek(0.5);

		const stored = JSON.parse(localStorage.getItem(RESUME_STORAGE_KEY) ?? 'null');
		expect(stored.articleId).toBe('a');
		expect(stored.progress).toBeGreaterThan(0.4);
	});

	it('resumes the same article from the remembered position', async () => {
		localStorage.setItem(RESUME_STORAGE_KEY, JSON.stringify({ articleId: 'a', progress: 0.5 }));

		const player = await started([A]);

		expect(player.progress).toBeGreaterThan(0.4);
	});

	it('starts another article from the beginning', async () => {
		localStorage.setItem(RESUME_STORAGE_KEY, JSON.stringify({ articleId: 'zzz', progress: 0.5 }));

		const player = await started([A]);

		expect(player.progress).toBe(0);
	});

	it('survives a corrupt resume record', async () => {
		localStorage.setItem(RESUME_STORAGE_KEY, '{not json');

		const player = await started([A]);

		expect(player.progress).toBe(0);
	});

	it('forgets the position once the article is finished', async () => {
		api.article.getArticle.mockResolvedValue(articleDetail('a', { content: '<p>Court.</p>' }));
		const player = await started([A]);

		while (engine.current()) engine.finish();

		await vi.waitFor(() => expect(player.current).toBeNull());
		expect(localStorage.getItem(RESUME_STORAGE_KEY)).toBeNull();
	});
});

describe('the media session', () => {
	it('publishes the article and answers the headset buttons', async () => {
		const handlers = new Map<string, () => void>();
		const session = {
			metadata: null as unknown,
			playbackState: 'none',
			setActionHandler: (action: string, handler: () => void) => handlers.set(action, handler)
		};
		vi.stubGlobal('navigator', { mediaSession: session });
		vi.stubGlobal(
			'MediaMetadata',
			class {
				constructor(public init: { title: string; artist: string }) {}
			}
		);

		const player = await started();

		expect((session.metadata as { init: { title: string } }).init.title).toBe('Premier');
		expect(session.playbackState).toBe('playing');

		handlers.get('pause')?.();
		expect(player.paused).toBe(true);

		handlers.get('nexttrack')?.();
		await vi.waitFor(() => expect(player.current?.id).toBe('b'));
	});
});


describe('a podcast episode', () => {
	class FakeAudio {
		static instances: FakeAudio[] = [];
		paused = true;
		duration = 100;
		currentTime = 0;
		playbackRate = 1;
		onended: (() => void) | null = null;
		onplay: (() => void) | null = null;
		onpause: (() => void) | null = null;
		onloadedmetadata: (() => void) | null = null;
		ontimeupdate: (() => void) | null = null;
		onerror: (() => void) | null = null;
		constructor(public src: string) {
			FakeAudio.instances.push(this);
		}
		play() {
			this.paused = false;
			this.onplay?.();
			return Promise.resolve();
		}
		pause() {
			this.paused = true;
			this.onpause?.();
		}
		removeAttribute() {}
	}

	const episode = articleSummary('ep', {
		title: 'Episode',
		enclosure_url: 'https://cdn.example.com/ep.mp3',
		enclosure_type: 'audio/mpeg'
	});

	beforeEach(() => {
		FakeAudio.instances = [];
		vi.stubGlobal('Audio', FakeAudio);
	});

	it('streams the file from its source instead of speaking it', async () => {
		const player = await started([episode]);

		expect(FakeAudio.instances[0].src).toBe('https://cdn.example.com/ep.mp3');
		expect(engine.spoken).toEqual([]);
		expect(api.article.getArticle).not.toHaveBeenCalled();
		expect(player.playing).toBe(true);
	});

	it('pauses and resumes the file', async () => {
		const player = await started([episode]);

		player.toggle();
		expect(player.paused).toBe(true);
		player.toggle();
		expect(player.playing).toBe(true);
	});

	it('tracks progress and seeks within the file', async () => {
		const player = await started([episode]);
		const audio = FakeAudio.instances[0];

		audio.currentTime = 25;
		audio.ontimeupdate?.();
		expect(player.progress).toBe(0.25);

		player.seek(0.5);
		expect(audio.currentTime).toBe(50);
	});

	it('resumes where the listener left off', async () => {
		localStorage.setItem(RESUME_STORAGE_KEY, JSON.stringify({ articleId: 'ep', progress: 0.4 }));
		await started([episode]);
		const audio = FakeAudio.instances[0];

		audio.onloadedmetadata?.();

		expect(audio.currentTime).toBe(40);
	});

	it('marks the episode read and moves on when it ends', async () => {
		const player = await started([episode, B]);

		FakeAudio.instances[0].onended?.();

		await vi.waitFor(() => expect(player.current?.id).toBe('b'));
		expect(api.recommendation.sendFeedback).toHaveBeenCalledWith('ep', { read: true });
	});

	it('applies the playback rate to the file', async () => {
		const player = await started([episode]);

		player.setRate(1.5);

		expect(FakeAudio.instances[0].playbackRate).toBe(1.5);
	});
});
