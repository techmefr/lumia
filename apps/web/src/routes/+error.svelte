<script lang="ts">
	import { base } from '$app/paths';
	import { page } from '$app/state';
	import { Button } from '@lumia/ui';
	import Compass from '@lucide/svelte/icons/compass';
	import { t } from '$technical/i18n/i18n.svelte';

	// A wrong url used to land on the router with nothing to show. Which of the two messages
	// applies is decided by the status alone: anything else is a failure, not a missing page.
	const notFound = $derived(page.status === 404);
</script>

<div
	class="mx-auto flex min-h-[60dvh] max-w-md flex-col items-center justify-center gap-4 text-center"
>
	<span class="flex size-14 items-center justify-center rounded-2xl bg-secondary text-primary">
		<Compass class="size-7" />
	</span>
	<h1 class="text-2xl font-bold">
		{notFound ? t('error.notFoundTitle') : t('error.genericTitle')}
	</h1>
	<p class="text-sm text-muted-foreground">
		{notFound ? t('error.notFoundBody') : t('error.genericBody')}
	</p>
	<Button href="{base}/articles">{t('common.browseArticles')}</Button>
</div>
