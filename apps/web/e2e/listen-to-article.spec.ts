import { expect, test } from '@playwright/test';
import { installTestSpeechEngine } from './support/speech-engine';

function collapse(value: string): string {
	return value.replace(/\s+/g, ' ').trim();
}

/**
 * Compared without any whitespace: the reader speaks the body's `textContent`, which runs two
 * paragraphs together with no separator, while `innerText` puts a line break between them. What
 * matters here is that every word is spoken, in order — not how the browser joins blocks.
 */
function squash(value: string): string {
	return value.replace(/\s+/g, '');
}

test('listening reads the whole article, chunk by chunk, then announces the end', async ({
	page
}) => {
	const engine = await installTestSpeechEngine(page);

	await page.goto('/articles');
	await page.locator('[data-test-article-card]').first().click();

	const heading = page.locator('[data-test-article-heading]');
	await expect(heading).toBeVisible();
	const title = collapse(await heading.innerText());
	const body = collapse(await page.locator('[data-test-article-content]').innerText());

	const listen = page.locator('[data-test-listen]');
	await listen.click();

	await expect(listen).toHaveAttribute('aria-pressed', 'true');
	await expect.poll(async () => (await engine.spoken()).length).toBeGreaterThan(0);

	const first = (await engine.spoken())[0];
	expect(squash(first).startsWith(squash(title))).toBe(true);

	await engine.playToEnd();

	await expect(page.locator('[data-test-toast-message]')).toBeVisible();
	await expect(listen).toHaveAttribute('aria-pressed', 'false');

	const spoken = await engine.spoken();
	// The bug this journey guards against is the reader jumping to the end: one utterance, or a
	// queue that stops after the title. So the article has to come out in several pieces, and the
	// pieces have to add up to the text on screen.
	expect(spoken.length).toBeGreaterThan(2);
	const heard = squash(spoken.join(' '));
	expect(heard).toBe(squash(`${title}. ${body}`));
});

test('listening can be paused and picked up again', async ({ page }) => {
	const engine = await installTestSpeechEngine(page);

	await page.goto('/articles');
	await page.locator('[data-test-article-card]').first().click();
	await expect(page.locator('[data-test-article-heading]')).toBeVisible();

	const listen = page.locator('[data-test-listen]');
	await listen.click();
	await expect(listen).toHaveAttribute('aria-pressed', 'true');

	await listen.click();
	await expect(listen).toHaveAttribute('aria-pressed', 'false');
	const whilePaused = (await engine.spoken()).length;

	await listen.click();
	await expect(listen).toHaveAttribute('aria-pressed', 'true');
	// Resuming re-speaks the chunk it stopped on, so the engine receives something new; a resume
	// that silently does nothing would leave this count untouched.
	await expect.poll(async () => (await engine.spoken()).length).toBeGreaterThan(whilePaused);
});
