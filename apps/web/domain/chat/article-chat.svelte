<script lang="ts">
	import { ApiError, type ChatAction, type ChatMessage, type ChatRequest } from '@lumia/core';
	import { Button, toast, Icon } from '@lumia/ui';
	import { Message01Icon } from '@hugeicons/core-free-icons';
	import { lumia } from '$technical/api/client';
	import { t, type MessageKey } from '$technical/i18n/i18n.svelte';
	import { diagramSource } from '$domain/chat/diagram-source';
	import MermaidDiagram from '$domain/chat/mermaid-diagram.svelte';

	interface Props {
		articleId: string;
	}

	const { articleId }: Props = $props();

	const MAX_MESSAGE_CHARS = 2000;
	const ACTIONS: ChatAction[] = ['summarize', 'explain', 'diagram'];
	const MAX_PASSAGE_CHARS = 4000;

	let open = $state(false);
	let loaded = $state(false);
	let messages = $state<ChatMessage[]>([]);
	let draft = $state('');
	let passage = $state<string | null>(null);
	let pending = $state(false);
	let error = $state<MessageKey | null>(null);

	async function toggle() {
		open = !open;
		if (!open || loaded) return;
		try {
			messages = await lumia.chat.listChat(articleId);
			loaded = true;
			error = null;
		} catch {
			error = 'chat.loadFailed';
		}
	}

	function takeSelection() {
		const selected = window.getSelection()?.toString().trim() ?? '';
		if (!selected) {
			error = 'chat.noSelection';
			return;
		}
		passage = selected.slice(0, MAX_PASSAGE_CHARS);
		error = null;
	}

	function withPassage(request: ChatRequest): ChatRequest {
		if (passage === null || ('action' in request && request.action === 'diagram')) return request;
		return { ...request, passage } as ChatRequest;
	}

	async function send(request: ChatRequest) {
		if (pending) return;
		pending = true;
		error = null;
		try {
			messages = [...messages, ...(await lumia.chat.sendChat(articleId, withPassage(request)))];
			draft = '';
			passage = null;
		} catch (failure) {
			error =
				failure instanceof ApiError && failure.status === 503
					? 'chat.unavailable'
					: 'chat.failed';
		} finally {
			pending = false;
		}
	}

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		const message = draft.trim();
		if (message) await send({ message });
	}

	async function clear() {
		try {
			await lumia.chat.clearChat(articleId);
			messages = [];
		} catch {
			toast(t('chat.failed'));
		}
	}

	function label(message: ChatMessage) {
		return message.action ? t(`chat.${message.action}`) : message.content;
	}
</script>

<section data-test-chat class="flex flex-col gap-3 print:hidden" aria-labelledby="article-chat-title">
	<h2 id="article-chat-title" class="text-lg font-semibold">
		<button
			type="button"
			data-test-chat-toggle
			aria-expanded={open}
			aria-controls="article-chat-panel"
			onclick={toggle}
			class="flex items-center gap-2 rounded-md hover:underline"
		>
			<Icon icon={Message01Icon} class="size-5" />
			{open ? t('chat.close') : t('chat.open')}
		</button>
	</h2>

	{#if open}
		<div id="article-chat-panel" class="flex flex-col gap-3 rounded-lg border p-3">
			<div role="log" aria-live="polite" aria-relevant="additions" data-test-chat-log>
				{#if messages.length === 0 && !pending}
					<p class="text-sm text-muted-foreground" data-test-chat-empty>{t('chat.empty')}</p>
				{/if}
				<ul class="flex flex-col gap-2">
					{#each messages as message (message.id)}
						<li
							data-test-chat-message={message.role}
							class="rounded-md p-2 text-sm whitespace-pre-wrap {message.role === 'user'
								? 'bg-secondary'
								: 'border'}"
						>
							<span class="font-semibold"
								>{message.role === 'user' ? t('chat.you') : t('chat.assistant')}
								<span class="sr-only">:</span></span
							>
							{label(message)}
							{#if message.passage}
								<blockquote data-test-chat-passage class="mt-1 border-s-2 ps-2 text-muted-foreground">
									{message.passage}
								</blockquote>
							{/if}
							{#if message.role === 'assistant' && diagramSource(message.content)}
								<MermaidDiagram source={diagramSource(message.content) ?? ''} />
							{/if}
						</li>
					{/each}
				</ul>
				{#if pending}
					<p class="text-sm text-muted-foreground" data-test-chat-pending>{t('chat.thinking')}</p>
				{/if}
			</div>

			{#if error}
				<p role="alert" class="text-sm text-destructive" data-test-chat-error>{t(error)}</p>
			{/if}

			<p class="text-xs text-muted-foreground" data-test-chat-privacy>{t('chat.privacy')}</p>

			{#if passage}
				<div class="flex items-start gap-2 rounded-md border p-2 text-sm" data-test-chat-selected-passage>
					<div class="flex-1">
						<p class="font-medium">{t('chat.passageLabel')}</p>
						<p class="line-clamp-3 text-muted-foreground">{passage}</p>
					</div>
					<Button
						type="button"
						variant="ghost"
						size="sm"
						data-test-chat-passage-remove
						onclick={() => (passage = null)}
					>
						{t('chat.removePassage')}
					</Button>
				</div>
			{/if}

			<div class="flex flex-wrap gap-2">
				<Button
					type="button"
					variant="outline"
					size="sm"
					disabled={pending}
					data-test-chat-use-passage
					onclick={takeSelection}
				>
					{t('chat.usePassage')}
				</Button>
				{#each ACTIONS as action (action)}
					<Button
						type="button"
						variant="outline"
						size="sm"
						disabled={pending}
						data-test-chat-action={action}
						onclick={() => send({ action })}
					>
						{t(`chat.${action}`)}
					</Button>
				{/each}
				{#if messages.length > 0}
					<Button
						type="button"
						variant="ghost"
						size="sm"
						disabled={pending}
						data-test-chat-clear
						onclick={clear}
					>
						{t('chat.clear')}
					</Button>
				{/if}
			</div>

			<form onsubmit={submit} class="flex flex-col gap-2">
				<label for="article-chat-input" class="text-sm font-medium">{t('chat.inputLabel')}</label>
				<textarea
					id="article-chat-input"
					data-test-chat-input
					bind:value={draft}
					maxlength={MAX_MESSAGE_CHARS}
					rows="3"
					class="w-full rounded-md border bg-background p-2 text-sm"
				></textarea>
				<Button type="submit" disabled={pending || draft.trim() === ''} data-test-chat-send>
					{pending ? t('chat.sending') : t('chat.send')}
				</Button>
			</form>
		</div>
	{/if}
</section>
