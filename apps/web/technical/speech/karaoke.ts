/**
 * Highlights the sentence currently being spoken, inside HTML the app does not own.
 *
 * The article body arrives as sanitised HTML and is injected as-is, so wrapping every sentence in a
 * span would mean re-parsing and rewriting it. The Custom Highlight API paints a Range instead,
 * touching neither the markup nor the layout. Where it is missing, the reading simply has no
 * highlight — the audio is unaffected.
 */

const HIGHLIGHT_NAME = 'lumia-tts';

interface FlatText {
	/** The concatenated text with runs of whitespace collapsed to one space. */
	text: string;
	/** For each character of `text`, the node it came from and its offset inside that node. */
	nodes: Text[];
	offsets: number[];
}

export function supportsKaraoke(): boolean {
	return typeof CSS !== 'undefined' && 'highlights' in CSS && typeof Highlight !== 'undefined';
}

export function clearKaraoke(): void {
	if (!supportsKaraoke()) return;
	CSS.highlights.delete(HIGHLIGHT_NAME);
}

/**
 * Paints `chunk` inside `root` and scrolls it into view when it has drifted off screen.
 * Returns false when the chunk is not part of `root` — the spoken title, typically.
 */
export function highlightChunk(root: HTMLElement, chunk: string): boolean {
	if (!supportsKaraoke()) return false;

	const needle = collapse(chunk);
	if (needle.length < 2) return false;

	const flat = flatten(root);
	const start = flat.text.indexOf(needle);
	if (start === -1) {
		clearKaraoke();
		return false;
	}
	const end = start + needle.length - 1;

	const range = document.createRange();
	range.setStart(flat.nodes[start], flat.offsets[start]);
	// End is exclusive, hence the +1 on the last character's offset.
	range.setEnd(flat.nodes[end], flat.offsets[end] + 1);

	CSS.highlights.set(HIGHLIGHT_NAME, new Highlight(range));
	scrollIntoViewIfNeeded(range);
	return true;
}

function collapse(value: string): string {
	return value.replace(/\s+/g, ' ').trim();
}

function flatten(root: HTMLElement): FlatText {
	const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
	let text = '';
	const nodes: Text[] = [];
	const offsets: number[] = [];
	let lastWasSpace = true;

	let node = walker.nextNode() as Text | null;
	while (node !== null) {
		const raw = node.data;
		for (let index = 0; index < raw.length; index += 1) {
			const isSpace = /\s/.test(raw[index]);
			// Collapse runs of whitespace the same way `collapse` does, so the needle built from
			// the spoken chunk and this haystack use one convention.
			if (isSpace && lastWasSpace) continue;
			text += isSpace ? ' ' : raw[index];
			nodes.push(node);
			offsets.push(index);
			lastWasSpace = isSpace;
		}
		node = walker.nextNode() as Text | null;
	}

	// A trailing space would never be part of a trimmed needle, so drop it rather than let it
	// shift the indices of a match at the very end.
	if (text.endsWith(' ')) {
		text = text.slice(0, -1);
		nodes.pop();
		offsets.pop();
	}
	return { text, nodes, offsets };
}

function scrollIntoViewIfNeeded(range: Range): void {
	const rect = range.getBoundingClientRect();
	if (rect.height === 0 && rect.width === 0) return;
	const margin = window.innerHeight * 0.25;
	if (rect.top >= margin && rect.bottom <= window.innerHeight - margin) return;
	window.scrollTo({
		top: window.scrollY + rect.top - window.innerHeight / 2,
		behavior: 'smooth'
	});
}
