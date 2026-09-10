/**
 * The width thresholds the app reacts to in script, named once so a layout rule and the JavaScript
 * that follows it cannot drift apart. The CSS side of the same thresholds lives in `app.css`
 * (`--container-app`, `--container-reading`) and in tailwind's own `sm`/`lg`/`xl`/`2xl` steps.
 */

/** Tailwind's `sm`: below it the article grid is a single column, whatever the display mode. */
export const MULTI_COLUMN_MIN_PX = 640;

export const COMPACT_VIEWPORT_QUERY = `(max-width: ${MULTI_COLUMN_MIN_PX - 1}px)`;

/**
 * Calls back with the current state right away, then on every crossing of the threshold. A resize
 * across it has to be handled and not only the width the page happened to load at: a mode picked
 * on a wide window must not stay in effect once the grid has collapsed to one column.
 */
export function watchCompactViewport(onChange: (compact: boolean) => void): () => void {
	if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
		onChange(false);
		return () => {};
	}
	const query = window.matchMedia(COMPACT_VIEWPORT_QUERY);
	const handle = () => onChange(query.matches);
	handle();
	query.addEventListener('change', handle);
	return () => query.removeEventListener('change', handle);
}
