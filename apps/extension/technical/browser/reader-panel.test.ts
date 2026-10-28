import { describe, expect, it } from 'vitest';
import { createFakeExtension } from '$test-support/fake-extension';
import { CURRENT_WINDOW_ID, openReaderPanel } from './reader-panel';

describe('openReaderPanel', () => {
	it('opens the chrome side panel on the current window', async () => {
		const fake = createFakeExtension({ sidePanel: true });
		await openReaderPanel(fake.extension);
		expect(fake.panelOpens).toEqual([`sidePanel:${CURRENT_WINDOW_ID}`]);
	});

	it('opens the firefox sidebar when there is no side panel', async () => {
		const fake = createFakeExtension({ sidebarAction: true });
		await openReaderPanel(fake.extension);
		expect(fake.panelOpens).toEqual(['sidebarAction']);
	});

	it('does nothing in a browser that has neither', async () => {
		const fake = createFakeExtension();
		await openReaderPanel(fake.extension);
		expect(fake.panelOpens).toEqual([]);
	});
});
