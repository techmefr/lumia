import { lumia } from '$technical/api/client';
import type { AudioSource } from './speech.svelte';

/**
 * Whether the account has a speech provider on file, asked once: every reading would otherwise
 * cost a round trip just to learn the same thing, and the answer only changes from the settings.
 */
let configured: Promise<boolean> | null = null;

export function resetServerVoice(): void {
	configured = null;
}

function hasServerVoice(): Promise<boolean> {
	configured ??= lumia.user
		.getMe()
		.then((me) => me.tts_provider !== null && me.tts_api_key_set)
		.catch(() => false);
	return configured;
}

/**
 * The recording of one article from the account's own provider, or null for the browser voice to
 * take over. Every way it can fail — no provider, article too long, provider down, rate limit —
 * leads to the same place, so none of them is told apart here.
 */
export function articleAudio(articleId: string): AudioSource {
	return async () => {
		try {
			if (!(await hasServerVoice())) return null;
			return await lumia.article.getArticleAudio(articleId);
		} catch {
			return null;
		}
	};
}
