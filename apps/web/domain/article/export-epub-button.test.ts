import { toasts } from '@lumia/ui';
import { fireEvent, render } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lumia } from '$technical/api/client';
import { setLocale } from '$technical/i18n/i18n.svelte';
import ExportEpubButton from './export-epub-button.svelte';

vi.mock('$technical/api/client', () => ({
	isDemo: false,
	lumia: { article: { exportArticleEpub: vi.fn() } }
}));

const api = vi.mocked(lumia.article);

type Props = Parameters<typeof ExportEpubButton>[1];

function widget(title = 'Un été à Paris') {
	const { container } = render(ExportEpubButton, { articleId: 'article-1', title } as Props);
	const button = () => container.querySelector<HTMLButtonElement>('[data-test-export-epub-button]')!;
	return { button, label: () => button().textContent?.trim().replace(/\s+/g, ' ') };
}

let download: { href: string; name: string } | null;

beforeEach(() => {
	setLocale('fr');
	download = null;
	for (const item of [...toasts.toasts]) toasts.dismiss(item.id);
	vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:epub');
	vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
	vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
		this: HTMLAnchorElement
	) {
		download = { href: this.href, name: this.download };
	});
});

afterEach(() => vi.restoreAllMocks());

describe('exporting an article as an epub', () => {
	it('offers the export', () => {
		expect(widget().label()).toBe('Exporter en EPUB');
	});

	it('asks for the epub of its own article and hands the file to the browser', async () => {
		api.exportArticleEpub.mockResolvedValue(new Blob(['epub']));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() => expect(download).not.toBeNull());
		expect(api.exportArticleEpub).toHaveBeenCalledWith('article-1');
		expect(download?.href).toBe('blob:epub');
		expect(download?.name).toBe('Un été à Paris.epub');
		expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:epub');
	});

	it('names the file after the title without the characters a file system refuses', async () => {
		api.exportArticleEpub.mockResolvedValue(new Blob(['epub']));
		const view = widget('Q/A: "Why?" <now>');

		await fireEvent.click(view.button());

		await vi.waitFor(() => expect(download).not.toBeNull());
		expect(download?.name).toBe('Q A Why now.epub');
	});

	it('falls back to a generic name when nothing is left of the title', async () => {
		api.exportArticleEpub.mockResolvedValue(new Blob(['epub']));
		const view = widget('???');

		await fireEvent.click(view.button());

		await vi.waitFor(() => expect(download).not.toBeNull());
		expect(download?.name).toBe('article.epub');
	});

	it('is busy and unclickable while the file is being prepared', async () => {
		let release: (blob: Blob) => void = () => undefined;
		api.exportArticleEpub.mockReturnValue(new Promise<Blob>((resolve) => (release = resolve)));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() => expect(view.button().disabled).toBe(true));
		expect(view.button().getAttribute('aria-busy')).toBe('true');
		expect(view.label()).toBe('Préparation de l’EPUB…');

		release(new Blob(['epub']));
		await vi.waitFor(() => expect(view.button().disabled).toBe(false));
	});

	it('tells the reader when the export fails and lets them try again', async () => {
		api.exportArticleEpub.mockRejectedValue(new Error('boom'));
		const view = widget();

		await fireEvent.click(view.button());

		await vi.waitFor(() =>
			expect(toasts.toasts.map((item) => item.message)).toContain(
				'Export EPUB impossible. Réessaie plus tard.'
			)
		);
		expect(download).toBeNull();
		expect(view.button().disabled).toBe(false);
	});
});
