<script lang="ts">
	import { base } from '$technical/paths/base';
	import { Badge, Button, toast } from '@lumia/ui';
	import Play from '@lucide/svelte/icons/play';
	import Pause from '@lucide/svelte/icons/pause';
	import SkipBack from '@lucide/svelte/icons/skip-back';
	import SkipForward from '@lucide/svelte/icons/skip-forward';
	import ChevronUp from '@lucide/svelte/icons/chevron-up';
	import ChevronDown from '@lucide/svelte/icons/chevron-down';
	import X from '@lucide/svelte/icons/x';
	import { t } from '$technical/i18n/i18n.svelte';
	import { SPEECH_FAILURE_MESSAGES } from '$technical/speech/speech.svelte';
	import { PLAYBACK_RATES, player } from './audio-player.svelte';

	let expanded = $state(false);

	const article = $derived(player.current);
	const percent = $derived(Math.round(player.progress * 100));

	// A reading that failed stops the queue; without a word on screen the player would look stuck.
	$effect(() => {
		const failure = player.error;
		if (failure) toast(t(SPEECH_FAILURE_MESSAGES[failure]));
	});

	function seekFromInput(event: Event) {
		player.seek(Number((event.currentTarget as HTMLInputElement).value) / 100);
	}
</script>

{#if article && player.supported}
	<section
		data-test-player
		aria-label={t('player.label')}
		class="fixed inset-x-0 z-40 border-t bg-card/95 backdrop-blur print:hidden sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-80 sm:rounded-2xl sm:border sm:shadow-lg"
		style="bottom: var(--bottom-nav-h, 0px)"
	>
		<div class="flex flex-col gap-2 p-3">
			{#if expanded}
				<div class="flex flex-col gap-2" data-test-player-details>
					{#if article.image_url}
						<img
							src={article.image_url}
							alt=""
							class="aspect-video w-full rounded-xl object-cover"
						/>
					{/if}
					<div class="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
						<span>{article.source_label}</span>
						{#if article.category_name}
							<Badge variant="secondary">{article.category_name}</Badge>
						{/if}
					</div>
				</div>
			{/if}

			<div class="flex items-center gap-2">
				<a
					href="{base}/articles/{article.id}"
					data-test-player-title
					class="min-w-0 flex-1 truncate text-sm font-medium hover:underline"
				>
					{article.title}
				</a>
				<Button
					data-test-player-expand
					variant="ghost"
					size="sm"
					aria-expanded={expanded}
					onclick={() => (expanded = !expanded)}
				>
					{#if expanded}
						<ChevronDown class="size-4" />
					{:else}
						<ChevronUp class="size-4" />
					{/if}
					<span class="sr-only">{expanded ? t('player.collapse') : t('player.expand')}</span>
				</Button>
				<Button data-test-player-close variant="ghost" size="sm" onclick={() => player.close()}>
					<X class="size-4" />
					<span class="sr-only">{t('player.close')}</span>
				</Button>
			</div>

			<input
				data-test-player-seek
				type="range"
				min="0"
				max="100"
				step="1"
				value={percent}
				oninput={seekFromInput}
				aria-label={t('player.seek')}
				aria-valuetext={t('player.seekValue', { percent })}
				class="w-full accent-primary"
			/>

			<div class="flex items-center justify-center gap-2">
				<Button
					data-test-player-previous
					variant="outline"
					size="sm"
					disabled={!player.hasPrevious}
					onclick={() => player.previous()}
				>
					<SkipBack class="size-4" />
					<span class="sr-only">{t('playlists.previous')}</span>
				</Button>
				<Button data-test-player-toggle onclick={() => player.toggle()}>
					{#if player.playing}
						<Pause class="size-4" />
						{t('playlists.pause')}
					{:else}
						<Play class="size-4" />
						{t('playlists.resume')}
					{/if}
				</Button>
				<Button
					data-test-player-next
					variant="outline"
					size="sm"
					disabled={!player.hasNext}
					onclick={() => player.next()}
				>
					<SkipForward class="size-4" />
					<span class="sr-only">{t('playlists.next')}</span>
				</Button>
			</div>

			{#if expanded}
				<fieldset class="flex items-center justify-center gap-1">
					<legend class="sr-only">{t('playlists.speed')}</legend>
					{#each PLAYBACK_RATES as value (value)}
						<label
							class="cursor-pointer rounded-md border px-2 py-1 text-xs transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring"
						>
							<input
								data-test-player-rate={value}
								type="radio"
								name="player-rate"
								{value}
								checked={player.rate === value}
								onchange={() => player.setRate(value)}
								class="sr-only"
							/>
							{value}×
						</label>
					{/each}
				</fieldset>
			{/if}

			<p data-test-player-status aria-live="polite" class="sr-only">
				{t('playlists.nowPlaying', { title: article.title })}
			</p>
		</div>
	</section>
{/if}
