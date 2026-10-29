<script lang="ts">
	import { onMount } from 'svelte';
	import { base } from '$technical/paths/base';
	import { ApiError, type Tag, type TagRef, type TagSuggestion } from '@lumia/core';
	import { Button, Input, toast } from '@lumia/ui';
	import Plus from '@lucide/svelte/icons/plus';
	import Sparkles from '@lucide/svelte/icons/sparkles';
	import X from '@lucide/svelte/icons/x';
	import { lumia } from '$technical/api/client';
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		articleId: string;
		tags: TagRef[];
		onchange: (tags: TagRef[]) => void;
	}

	const { articleId, tags, onchange }: Props = $props();

	let draft = $state('');
	let known = $state<Tag[]>([]);
	let suggestions = $state<TagSuggestion[]>([]);
	let dismissed = $state<string[]>([]);
	let asking = $state(false);
	let saving = $state(false);

	// Compared casefolded, as the backend does, so a suggestion for « cuisine » disappears once
	// « Cuisine » is on the article.
	const carried = $derived(new Set(tags.map((tag) => tag.name.toLowerCase())));
	const visible = $derived(
		suggestions.filter(
			(item) =>
				!carried.has(item.name.toLowerCase()) && !dismissed.includes(item.name.toLowerCase())
		)
	);

	async function loadSuggestions() {
		try {
			[known, suggestions] = await Promise.all([
				lumia.tag.listTags(),
				lumia.tag.getSuggestions(articleId)
			]);
		} catch {
			// Suggestions are a convenience: the editor works without them.
		}
	}

	async function attach(name: string) {
		const trimmed = name.trim();
		if (!trimmed) return;
		saving = true;
		try {
			onchange(await lumia.tag.tagArticle(articleId, trimmed));
			draft = '';
			known = await lumia.tag.listTags();
		} catch {
			toast(t('tags.saveFailed'), { tone: 'destructive' });
		} finally {
			saving = false;
		}
	}

	async function detach(tag: TagRef) {
		try {
			onchange(await lumia.tag.untagArticle(articleId, tag.id));
		} catch {
			toast(t('tags.saveFailed'), { tone: 'destructive' });
		}
	}

	function submit(event: SubmitEvent) {
		event.preventDefault();
		void attach(draft);
	}

	function dismiss(item: TagSuggestion) {
		dismissed = [...dismissed, item.name.toLowerCase()];
	}

	function aiMessage(error: unknown) {
		if (error instanceof ApiError && error.status === 503) return t('tags.aiUnavailable');
		return t('tags.aiFailed');
	}

	async function askAi() {
		asking = true;
		try {
			const fromModel = await lumia.tag.getAiSuggestions(articleId);
			const have = new Set(suggestions.map((item) => item.name.toLowerCase()));
			const fresh = fromModel.filter((item) => !have.has(item.name.toLowerCase()));
			if (fresh.length === 0) toast(t('tags.aiNone'));
			suggestions = [...suggestions, ...fresh];
		} catch (error) {
			toast(aiMessage(error), { tone: 'destructive' });
		} finally {
			asking = false;
		}
	}

	onMount(loadSuggestions);
</script>

<section data-test-article-tags aria-labelledby="article-tags-title" class="mt-4 flex flex-col gap-2">
	<h2 id="article-tags-title" class="text-sm font-semibold text-muted-foreground">
		{t('tags.title')}
	</h2>

	{#if tags.length > 0}
		<ul class="flex flex-wrap gap-1.5">
			{#each tags as tag (tag.id)}
				<li
					data-test-tag={tag.id}
					class="flex items-center rounded-full bg-secondary text-sm text-secondary-foreground"
				>
					<a
						data-test-tag-link
						href="{base}/articles?tag_id={tag.id}&tag_name={encodeURIComponent(tag.name)}"
						class="min-h-8 rounded-l-full py-1 pr-1 pl-3 hover:underline"
					>
						{tag.name}
					</a>
					<button
						data-test-tag-remove
						type="button"
						onclick={() => detach(tag)}
						class="flex min-h-8 min-w-8 items-center justify-center rounded-r-full hover:bg-secondary/70"
					>
						<X class="size-3.5" aria-hidden="true" />
						<span class="sr-only">{t('tags.remove', { name: tag.name })}</span>
					</button>
				</li>
			{/each}
		</ul>
	{/if}

	<form class="flex flex-wrap items-end gap-2" onsubmit={submit}>
		<label class="flex flex-1 flex-col gap-1 text-sm">
			<span class="font-medium">{t('tags.label')}</span>
			<Input
				data-test-tag-input
				bind:value={draft}
				list="article-tags-known"
				maxlength={40}
				placeholder={t('tags.placeholder')}
			/>
		</label>
		<datalist id="article-tags-known">
			{#each known as option (option.id)}
				<option value={option.name}></option>
			{/each}
		</datalist>
		<Button data-test-tag-submit type="submit" disabled={saving || draft.trim() === ''}>
			<Plus class="size-4" aria-hidden="true" />
			{t('common.add')}
		</Button>
	</form>

	<div class="flex flex-wrap items-center gap-1.5" role="group" aria-label={t('tags.suggested')}>
		{#each visible as item (item.name)}
			<span
				data-test-suggestion={item.name}
				data-test-suggestion-source={item.source}
				class="flex items-center rounded-full border border-dashed text-sm text-muted-foreground"
			>
				<button
					data-test-suggestion-accept
					type="button"
					onclick={() => attach(item.name)}
					class="flex min-h-8 items-center gap-1 rounded-l-full py-1 pr-1 pl-3 hover:text-foreground"
				>
					<Plus class="size-3.5" aria-hidden="true" />
					{item.name}
					<span class="sr-only">{t('tags.accept', { name: item.name })}</span>
				</button>
				<button
					data-test-suggestion-dismiss
					type="button"
					onclick={() => dismiss(item)}
					class="flex min-h-8 min-w-8 items-center justify-center rounded-r-full hover:text-foreground"
				>
					<X class="size-3.5" aria-hidden="true" />
					<span class="sr-only">{t('tags.dismiss', { name: item.name })}</span>
				</button>
			</span>
		{/each}
		<button
			data-test-tag-ai
			type="button"
			onclick={askAi}
			disabled={asking}
			aria-busy={asking}
			class="flex min-h-8 items-center gap-1.5 rounded-md px-2 text-sm text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground disabled:opacity-60"
		>
			<Sparkles class="size-4" aria-hidden="true" />
			{t('tags.askAi')}
		</button>
	</div>
</section>
