<script lang="ts">
	import { t } from '$technical/i18n/i18n.svelte';

	interface Props {
		source: string;
	}

	const { source }: Props = $props();

	let svg = $state<string | null>(null);
	let failed = $state(false);
	let renderId = 0;

	$effect(() => {
		const current = source;
		const id = `lumia-diagram-${++renderId}`;
		svg = null;
		failed = false;
		void draw(current, id);
	});

	async function draw(text: string, id: string) {
		try {
			const { default: mermaid } = await import('mermaid');
			mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
			const result = await mermaid.render(id, text);
			if (text === source) svg = result.svg;
		} catch {
			if (text === source) failed = true;
		}
	}
</script>

{#if svg}
	<figure data-test-chat-diagram class="overflow-x-auto" aria-label={t('chat.diagramLabel')}>
		{@html svg}
	</figure>
{:else if failed}
	<div data-test-chat-diagram-failed class="flex flex-col gap-1">
		<p role="alert" class="text-sm text-destructive">{t('chat.diagramFailed')}</p>
		<pre class="overflow-x-auto rounded-md bg-secondary p-2 text-xs">{source}</pre>
	</div>
{/if}
