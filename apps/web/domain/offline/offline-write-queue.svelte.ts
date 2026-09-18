import type { FeedbackUpdate } from '@lumia/core';
import type { OfflineDatabase, PendingWriteRecord } from '$technical/offline/offline-database';

function generateId(): string {
	return typeof crypto !== 'undefined' && 'randomUUID' in crypto
		? crypto.randomUUID()
		: `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Reading position, read state and votes made while offline, replayed once the network is back.
 *
 * Every field in `FeedbackUpdate` is an absolute value, not a delta — `scroll_progress` is the
 * fraction reached, `sentiment`/`saved`/`favorite` are the state to end up in, and the server keeps
 * the highest `scroll_progress` it has ever seen (see `feedback_service.apply_feedback`), so it
 * never rewinds. That is what makes replaying safe: sending the same write twice, or an update that
 * has since gone stale, lands on the same state either way. Coalescing on enqueue is done anyway,
 * so a reconnect after a long offline session sends one request per article instead of a burst of
 * every scroll tick recorded while offline — the "vote rejoué deux fois" case above is inherently
 * safe, this just keeps the replay small.
 */
export class OfflineWriteQueue {
	private db: OfflineDatabase;
	pending = $state<PendingWriteRecord[]>([]);

	constructor(db: OfflineDatabase) {
		this.db = db;
	}

	get pendingCount(): number {
		return this.pending.length;
	}

	async init(): Promise<void> {
		this.pending = await this.db.listPendingWrites();
	}

	/** Merges into an already-queued write for the same article rather than piling up a new one. */
	async enqueue(articleId: string, payload: FeedbackUpdate): Promise<void> {
		const existing = this.pending.find((record) => record.articleId === articleId);
		const record: PendingWriteRecord = existing
			? { ...existing, payload: { ...existing.payload, ...payload } }
			: { id: generateId(), articleId, payload, createdAt: Date.now() };

		await this.db.enqueueWrite(record);
		this.pending = existing
			? this.pending.map((current) => (current.id === record.id ? record : current))
			: [...this.pending, record];
	}

	/**
	 * Replays every pending write, oldest first, stopping at the first failure: a failure past the
	 * initial reconnect almost always means the connection dropped again, and the remaining writes
	 * should wait for the next attempt rather than being attempted out of order.
	 */
	async flush(sendFeedback: (articleId: string, payload: FeedbackUpdate) => Promise<void>): Promise<{
		synced: number;
		remaining: number;
	}> {
		const ordered = [...this.pending].sort((a, b) => a.createdAt - b.createdAt);
		let synced = 0;

		for (const record of ordered) {
			try {
				await sendFeedback(record.articleId, record.payload);
			} catch {
				break;
			}
			await this.db.deletePendingWrite(record.id);
			this.pending = this.pending.filter((current) => current.id !== record.id);
			synced += 1;
		}

		return { synced, remaining: this.pending.length };
	}
}
