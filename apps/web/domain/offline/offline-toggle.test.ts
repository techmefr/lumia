import { render, fireEvent } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import OfflineToggle from './offline-toggle.svelte';

type Props = Parameters<typeof OfflineToggle>[1];

function toggle(props: Partial<Props> = {}) {
	const onToggle = vi.fn();
	const { container } = render(OfflineToggle, {
		articleId: 'a1',
		offline: false,
		onToggle,
		...props
	} as Props);
	return { container, onToggle, button: () => container.querySelector<HTMLButtonElement>('[data-test-offline-toggle="a1"]') };
}

describe('offline toggle', () => {
	it('is not pressed when the article is not offline', () => {
		expect(toggle({ offline: false }).button()?.getAttribute('aria-pressed')).toBe('false');
	});

	it('is pressed when the article is offline', () => {
		expect(toggle({ offline: true }).button()?.getAttribute('aria-pressed')).toBe('true');
	});

	it('runs the handler on click', async () => {
		const view = toggle();
		await fireEvent.click(view.button() as HTMLButtonElement);
		expect(view.onToggle).toHaveBeenCalledOnce();
	});

	it('disables itself while a toggle is already in flight, so a second click cannot race it', () => {
		expect(toggle({ pending: true }).button()?.disabled).toBe(true);
	});

	it('names the action for a screen reader, and the name flips with the state', () => {
		expect(toggle({ offline: false }).button()?.getAttribute('aria-label')).toBe('Make available offline');
		expect(toggle({ offline: true }).button()?.getAttribute('aria-label')).toBe('Remove from offline');
	});
});
