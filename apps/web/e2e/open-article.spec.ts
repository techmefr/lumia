import { expect, test } from '@playwright/test';

test('opening a card from the list shows that article', async ({ page }) => {
	await page.goto('/articles');

	const grid = page.locator('[data-test-article-grid]');
	await expect(grid).toBeVisible();

	const card = grid.locator('[data-test-article-card]').first();
	const articleId = await card.getAttribute('data-test-article-card');
	const cardTitle = (await card.locator('[data-test-article-title]').innerText()).trim();
	expect(articleId).toBeTruthy();
	expect(cardTitle.length).toBeGreaterThan(0);

	await card.click();

	await expect(page).toHaveURL(new RegExp(`/articles/${articleId}$`));
	await expect(page.locator('[data-test-article-heading]')).toHaveText(cardTitle);
	// The body, not just the heading: a detail page that renders its title and nothing else is the
	// failure this journey exists to catch.
	await expect(page.locator('[data-test-article-content] p').first()).toBeVisible();
});

test('going back from an article returns to the list', async ({ page }) => {
	await page.goto('/articles');

	const card = page.locator('[data-test-article-card]').first();
	await expect(card).toBeVisible();
	await card.click();

	await expect(page.locator('[data-test-article-heading]')).toBeVisible();

	await page.locator('[data-test-article-back]').click();

	await expect(page).toHaveURL(/\/articles$/);
	await expect(page.locator('[data-test-article-grid]')).toBeVisible();
});
