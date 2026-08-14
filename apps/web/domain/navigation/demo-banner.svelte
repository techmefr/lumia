<script lang="ts">
	import { base } from '$app/paths';
	import FlaskConical from '@lucide/svelte/icons/flask-conical';
	import { resetDemo } from '$technical/api/demo/demo-client';

	function reset() {
		resetDemo();
		// A full reload is the honest way to rebuild the seeded state: every page holds its own
		// copy of what it loaded, and there is no store to invalidate across them.
		window.location.href = `${base}/articles`;
	}
</script>

<div
	class="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 border-b bg-primary/10 px-4 py-1.5 text-center text-xs text-foreground"
>
	<span class="flex items-center gap-1.5 font-medium">
		<FlaskConical class="size-3.5 text-primary" />
		Démo — données fictives, tout se passe dans ce navigateur
	</span>
	<button type="button" onclick={reset} class="underline underline-offset-2 hover:text-primary">
		Réinitialiser
	</button>
	<a
		href="https://github.com/techmefr/lumia"
		class="underline underline-offset-2 hover:text-primary"
	>
		Le code
	</a>
</div>
