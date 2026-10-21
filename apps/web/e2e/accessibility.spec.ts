import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const WCAG_AA_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

const PAGES = [
	'/articles',
	'/etincelle',
	'/feeds',
	'/a-lire-plus-tard',
	'/playlists',
	'/favoris',
	'/surlignages',
	'/statistiques',
	'/alerts',
	'/settings'
] as const;

for (const scheme of ['light', 'dark'] as const) {
	for (const path of PAGES) {
		test(`${path} has no WCAG 2.1 AA violation in ${scheme} mode`, async ({ page }) => {
			await page.emulateMedia({ colorScheme: scheme });
			await page.addInitScript((value) => localStorage.setItem('lumia-theme', value), scheme);
			await page.goto(path);
			await expect(page.locator('[data-test-main]')).toBeVisible();
			await page.waitForLoadState('networkidle');

			const results = await new AxeBuilder({ page }).withTags(WCAG_AA_TAGS).analyze();

			const summary = results.violations.map(
				(violation) =>
					`${violation.id} (${violation.impact}): ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`
			);
			expect(summary).toEqual([]);
		});
	}
}

test('the spark mode can be driven with the arrow keys alone', async ({ page }) => {
	await page.goto('/etincelle');
	const title = page.locator('[data-test-swipe-card="top"] h2');
	await expect(title).toBeVisible();
	const first = await title.innerText();

	await page.keyboard.press('ArrowRight');

	await expect(page.locator('[data-test-swipe-announcement]')).toContainText(first);
	await expect(title).not.toHaveText(first);
});
