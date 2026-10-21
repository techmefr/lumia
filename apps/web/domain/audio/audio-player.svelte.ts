import type { ArticleSummary } from '@lumia/core';
import { toast } from '@lumia/ui';
import { t } from '$technical/i18n/i18n.svelte';
import { lumia } from '$technical/api/client';
import { SpeechReader } from '$technical/speech/speech.svelte';
import { readableText } from '$technical/speech/readable-text';
import { articleAudio } from '$technical/speech/server-voice';

export const PLAYBACK_RATES = [0.8, 1, 1.25, 1.5];

export const RESUME_STORAGE_KEY = 'lumia.player.resume';

const SEEK_STEP = 0.05;

interface ResumePoint {
	articleId: string;
	progress: number;
}

function readResumePoint(): ResumePoint | null {
	try {
		const raw = localStorage.getItem(RESUME_STORAGE_KEY);
		if (!raw) return null;
		const parsed = JSON.parse(raw) as Partial<ResumePoint>;
		if (typeof parsed.articleId !== 'string' || typeof parsed.progress !== 'number') return null;
		return { articleId: parsed.articleId, progress: parsed.progress };
	} catch {
		return null;
	}
}

function writeResumePoint(point: ResumePoint | null): void {
	try {
		if (point) localStorage.setItem(RESUME_STORAGE_KEY, JSON.stringify(point));
		else localStorage.removeItem(RESUME_STORAGE_KEY);
	} catch {
		// Storage can be full or blocked; losing the resume point only costs a restart.
	}
}

/**
 * The one reader of the app. It lives outside any page so a reading survives navigation: the
 * layout shows it, the pages only hand it articles.
 */
export class AudioPlayer {
	queue = $state<ArticleSummary[]>([]);
	index = $state(-1);
	rate = $state(1);

	private readonly reader = new SpeechReader();
	/** The podcast file being streamed from its source, when the current article carries one. */
	private enclosure: HTMLAudioElement | null = null;
	private enclosureState = $state({ playing: false, progress: 0 });
	/** Bumped on every article change so a body fetched for a skipped article is ignored. */
	private generation = 0;

	get supported(): boolean {
		return this.reader.supported || Boolean(this.current?.enclosure_url);
	}

	get current(): ArticleSummary | null {
		return this.queue[this.index] ?? null;
	}

	get playing(): boolean {
		if (this.enclosure) return this.enclosureState.playing;
		return this.reader.speaking && !this.reader.paused;
	}

	get paused(): boolean {
		if (this.enclosure) return !this.enclosureState.playing;
		return this.reader.paused;
	}

	/** 0 to 1 within the current article. */
	get progress(): number {
		return this.enclosure ? this.enclosureState.progress : this.reader.progress;
	}

	get error() {
		return this.reader.error;
	}

	get hasNext(): boolean {
		return this.index < this.queue.length - 1;
	}

	get hasPrevious(): boolean {
		return this.index > 0;
	}

	/** Replaces the queue and starts at `startIndex`. */
	async play(articles: ArticleSummary[], startIndex = 0): Promise<void> {
		this.queue = [...articles];
		await this.playAt(startIndex);
	}

	/** Appends without interrupting; starts it when nothing is loaded. */
	async enqueue(article: ArticleSummary): Promise<void> {
		if (this.queue.some((queued) => queued.id === article.id)) return;
		this.queue = [...this.queue, article];
		if (this.current === null) {
			await this.playAt(this.queue.length - 1);
		}
	}

	toggle(): void {
		if (this.enclosure) {
			if (this.enclosure.paused) void this.enclosure.play().catch(() => {});
			else this.enclosure.pause();
		} else if (this.reader.paused) {
			this.reader.resume();
			this.syncMediaSession();
		} else if (this.reader.speaking) {
			this.reader.pause();
			this.syncMediaSession();
		} else if (this.current) {
			void this.playAt(this.index);
		}
	}

	next(): Promise<void> {
		return this.playAt(this.index + 1);
	}

	previous(): Promise<void> {
		return this.playAt(Math.max(this.index - 1, 0));
	}

	seek(fraction: number): void {
		if (this.enclosure) {
			if (this.enclosure.duration > 0) this.enclosure.currentTime = fraction * this.enclosure.duration;
		} else {
			this.reader.seek(fraction);
		}
		this.persist(fraction);
	}

	seekBy(delta: number): void {
		this.seek(Math.min(Math.max(this.progress + delta, 0), 1));
	}

	skipForward(): void {
		this.seekBy(SEEK_STEP);
	}

	skipBackward(): void {
		this.seekBy(-SEEK_STEP);
	}

	setRate(rate: number): void {
		this.rate = rate;
		if (this.enclosure) this.enclosure.playbackRate = rate;
		this.reader.setRate(rate);
	}

	/** Empties the queue and goes silent. */
	close(): void {
		this.generation += 1;
		this.reader.stop();
		this.releaseEnclosure();
		this.queue = [];
		this.index = -1;
		writeResumePoint(null);
		this.syncMediaSession();
	}

	/** Silences the player without forgetting the queue, for a screen that reads on its own. */
	yield(): void {
		this.generation += 1;
		this.reader.stop();
		this.releaseEnclosure();
	}

	private async playAt(position: number): Promise<void> {
		const article = this.queue[position];
		const generation = ++this.generation;
		this.releaseEnclosure();
		if (!article) {
			this.reader.stop();
			this.index = -1;
			this.queue = [];
			writeResumePoint(null);
			this.syncMediaSession();
			return;
		}

		this.index = position;
		this.syncMediaSession();
		if (article.enclosure_url) {
			this.reader.stop();
			this.startEnclosure(article, article.enclosure_url, position);
			return;
		}
		let text = article.summary ?? '';
		try {
			// The list only carries the summary; the body has to be fetched to read it in full.
			const detail = await lumia.article.getArticle(article.id);
			text = readableText(new DOMParser().parseFromString(detail.content, 'text/html').body) || text;
		} catch {
			// Fall back on the summary rather than skipping the article silently.
		}
		if (generation !== this.generation) return;

		const resume = readResumePoint();
		const startAt = resume?.articleId === article.id ? resume.progress : 0;
		this.reader.speak(`${article.title}. ${text}`, {
			rate: this.rate,
			startAt,
			audio: articleAudio(article.id),
			onProgress: (progress) => this.persist(progress),
			onDone: () => {
				void lumia.recommendation.sendFeedback(article.id, { read: true }).catch(() => {});
				writeResumePoint(null);
				void this.playAt(position + 1);
			}
		});
		this.syncMediaSession();
	}

	/** Streams straight from the feed's host: the instance never downloads or stores the file. */
	private startEnclosure(article: ArticleSummary, url: string, position: number): void {
		const audio = new Audio(url);
		audio.playbackRate = this.rate;
		const resume = readResumePoint();
		const startAt = resume?.articleId === article.id ? resume.progress : 0;
		audio.onloadedmetadata = () => {
			if (startAt > 0 && audio.duration > 0) audio.currentTime = startAt * audio.duration;
		};
		audio.ontimeupdate = () => {
			if (audio.duration > 0) {
				this.enclosureState.progress = audio.currentTime / audio.duration;
				this.persist(this.enclosureState.progress);
			}
		};
		audio.onplay = () => {
			this.enclosureState.playing = true;
			this.syncMediaSession();
		};
		audio.onpause = () => {
			this.enclosureState.playing = false;
			this.syncMediaSession();
		};
		audio.onended = () => {
			void lumia.recommendation.sendFeedback(article.id, { read: true }).catch(() => {});
			writeResumePoint(null);
			void this.playAt(position + 1);
		};
		audio.onerror = () => {
			this.releaseEnclosure();
			toast(t('player.enclosureFailed'));
		};
		this.enclosureState.progress = startAt;
		this.enclosure = audio;
		void audio.play().catch(() => {});
	}

	private releaseEnclosure(): void {
		const audio = this.enclosure;
		if (!audio) return;
		audio.onloadedmetadata = null;
		audio.ontimeupdate = null;
		audio.onplay = null;
		audio.onpause = null;
		audio.onended = null;
		audio.onerror = null;
		audio.pause();
		audio.removeAttribute('src');
		this.enclosure = null;
		this.enclosureState = { playing: false, progress: 0 };
	}

	private persist(progress: number): void {
		const article = this.current;
		if (article) writeResumePoint({ articleId: article.id, progress });
	}

	/** Lets the lock screen and the headset buttons drive the player. */
	private syncMediaSession(): void {
		if (typeof navigator === 'undefined' || !('mediaSession' in navigator)) return;
		const session = navigator.mediaSession;
		const article = this.current;
		if (!article) {
			session.metadata = null;
			session.playbackState = 'none';
			return;
		}
		session.metadata = new MediaMetadata({
			title: article.title,
			artist: article.source_label,
			artwork: article.image_url ? [{ src: article.image_url }] : []
		});
		session.playbackState = this.playing ? 'playing' : 'paused';
		const handlers: [MediaSessionAction, MediaSessionActionHandler][] = [
			['play', () => this.toggle()],
			['pause', () => this.toggle()],
			['nexttrack', () => void this.next()],
			['previoustrack', () => void this.previous()],
			['seekforward', () => this.skipForward()],
			['seekbackward', () => this.skipBackward()]
		];
		for (const [action, handler] of handlers) {
			try {
				session.setActionHandler(action, handler);
			} catch {
				// An engine that lacks an action just does not offer that button.
			}
		}
	}
}

export const player = new AudioPlayer();
