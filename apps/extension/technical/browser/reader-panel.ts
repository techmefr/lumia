import type { ExtensionApi } from './extension-api';

export const CURRENT_WINDOW_ID = -2;

export async function openReaderPanel(extension: ExtensionApi): Promise<void> {
	if (extension.sidePanel) {
		await extension.sidePanel.open({ windowId: CURRENT_WINDOW_ID });
		return;
	}
	await extension.sidebarAction?.open();
}
