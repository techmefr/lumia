<script lang="ts">
	import { base } from '$app/paths';
	import type { Highlight } from '@lumia/core';
	import { Button } from '@lumia/ui';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		highlight: Highlight;
		/** The passage is no longer in the article text; the note is still shown. */
		orphaned?: boolean;
		showArticle?: boolean;
		/** Resolves false when saving failed, which keeps the field open; the owner reports why. */
		onsavenote: (note: string | null) => Promise<boolean>;
		ondelete: () => Promise<void>;
		/** Absent when the passage cannot be scrolled to, which hides the button. */
		onreveal?: () => void;
	}

	let { highlight, orphaned = false, showArticle = false, onsavenote, ondelete, onreveal }: Props =
		$props();

	let editing = $state(false);
	let draft = $state('');
	let busy = $state(false);
	let noteField = $state<HTMLTextAreaElement | null>(null);

	async function startEditing() {
		draft = highlight.note ?? '';
		editing = true;
		await Promise.resolve();
		noteField?.focus();
	}

	async function save() {
		if (busy) return;
		busy = true;
		try {
			const trimmed = draft.trim();
			if (await onsavenote(trimmed === '' ? null : trimmed)) editing = false;
		} finally {
			busy = false;
		}
	}

	async function remove() {
		if (busy) return;
		busy = true;
		try {
			await ondelete();
		} finally {
			busy = false;
		}
	}

	const noteId = $derived(`highlight-note-${highlight.id}`);
</script>

<li data-test-highlight={highlight.id} class="flex flex-col gap-2 rounded-lg border p-3">
	{#if showArticle}
		<a
			data-test-highlight-article
			href="{base}/articles/{highlight.article_id}"
			class="w-fit text-xs text-primary hover:underline"
		>
			{highlight.article_title}
		</a>
	{/if}

	<blockquote data-test-highlight-quote class="border-s-2 border-primary ps-3 font-serif text-sm">
		{highlight.quote}
	</blockquote>

	{#if orphaned}
		<p data-test-highlight-orphan class="text-xs text-muted-foreground">
			{t('highlights.orphan')}
		</p>
	{/if}

	{#if editing}
		<div class="flex flex-col gap-2">
			<label for={noteId} class="text-xs font-medium">{t('highlights.noteLabel')}</label>
			<textarea
				id={noteId}
				data-test-highlight-note-field
				bind:this={noteField}
				bind:value={draft}
				rows="3"
				maxlength="2000"
				class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
			></textarea>
			<div class="flex gap-2">
				<Button data-test-highlight-note-save size="sm" disabled={busy} onclick={save}>
					{t('common.save')}
				</Button>
				<Button
					data-test-highlight-note-cancel
					size="sm"
					variant="outline"
					onclick={() => (editing = false)}
				>
					{t('common.cancel')}
				</Button>
			</div>
		</div>
	{:else}
		{#if highlight.note}
			<p data-test-highlight-note class="whitespace-pre-wrap text-sm text-muted-foreground">
				{highlight.note}
			</p>
		{/if}
		<div class="flex flex-wrap gap-2">
			<Button data-test-highlight-edit size="sm" variant="outline" onclick={startEditing}>
				{highlight.note ? t('highlights.editNote') : t('highlights.addNote')}
			</Button>
			{#if onreveal}
				<Button data-test-highlight-reveal size="sm" variant="outline" onclick={onreveal}>
					{t('highlights.show')}
				</Button>
			{/if}
			<Button
				data-test-highlight-delete
				size="sm"
				variant="outline"
				disabled={busy}
				onclick={remove}
			>
				{t('highlights.delete')}
			</Button>
		</div>
	{/if}
</li>
