import { expect, test } from '@playwright/test';

const DESTINATIONS = [
	{ href: '/etincelle', page: 'etincelle' },
	{ href: '/feeds', page: 'feeds' },
	{ href: '/a-lire-plus-tard', page: 'read-later' },
	{ href: '/playlists', page: 'playlists' }
] as const;

test('the main navigation reaches every section and marks the current one', async ({ page }) => {
	await page.goto('/articles');
	await expect(page.locator('[data-test-page="articles"]')).toBeVisible();

	for (const destination of DESTINATIONS) {
		const link = page.locator(`[data-test-nav-link="${destination.href}"]`);
		await link.click();

		await expect(page).toHaveURL(new RegExp(`${destination.href}$`));
		await expect(page.locator(`[data-test-page="${destination.page}"]`)).toBeVisible();
		await expect(link).toHaveAttribute('aria-current', 'page');
	}

	await page.locator('[data-test-nav-link="/articles"]').click();
	await expect(page.locator('[data-test-article-grid]')).toBeVisible();
});

test('a deep link boots straight into the article it names', async ({ page }) => {
	await page.goto('/articles');
	const card = page.locator('[data-test-article-card]').first();
	await expect(card).toBeVisible();
	const articleId = await card.getAttribute('data-test-article-card');

	// Entering by URL rather than by click: the static SPA has no server route for this path, and
	// the fallback shell booting the router is what makes a shared link work at all.
	await page.goto(`/articles/${articleId}`);

	await expect(page.locator('[data-test-article-heading]')).toBeVisible();
	await expect(page.locator('[data-test-article-content] p').first()).toBeVisible();
});
