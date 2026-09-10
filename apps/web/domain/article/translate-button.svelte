<script lang="ts">
	import { ApiError, type ArticleTranslation } from '@lumia/core';
	import { toast } from '@lumia/ui';
	import Languages from '@lucide/svelte/icons/languages';
	import Loader2 from '@lucide/svelte/icons/loader-2';
	import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
	import { lumia } from '$technical/api/client';
	import { getLocale, t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articleId: string;
		/** The translation currently on screen, or null while the reader is on the original. */
		translation: ArticleTranslation | null;
		onchange: (translation: ArticleTranslation | null) => void;
	}

	const { articleId, translation, onchange }: Props = $props();

	let pending = $state(false);

	/**
	 * 503 is the provider saying "not for this account, not for this language" rather than a
	 * failure: the reader is told what to do about it instead of being shown an error.
	 */
	function messageFor(error: unknown) {
		if (error instanceof ApiError && error.status === 503) return t('article.translateUnavailable');
		return t('article.translateFailed');
	}

	async function translate() {
		if (translation) {
			onchange(null);
			return;
		}
		pending = true;
		try {
			onchange(await lumia.article.translateArticle(articleId, getLocale()));
		} catch (error) {
			toast(messageFor(error));
		} finally {
			pending = false;
		}
	}
</script>

<button
	type="button"
	onclick={translate}
	disabled={pending}
	aria-busy={pending}
	aria-pressed={translation !== null}
	data-test-translate-button
	data-test-translate-state={pending ? 'pending' : translation ? 'translated' : 'original'}
	class="flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:cursor-not-allowed disabled:opacity-60"
>
	{#if pending}
		<Loader2 class="size-4 animate-spin" aria-hidden="true" />
		{t('article.translating')}
	{:else if translation}
		<RotateCcw class="size-4 text-primary" aria-hidden="true" />
		{t('article.showOriginal')}
	{:else}
		<Languages class="size-4" aria-hidden="true" />
		{t('article.translate')}
	{/if}
</button>
