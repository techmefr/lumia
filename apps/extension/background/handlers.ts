import type { ExtensionApi } from '$technical/browser/extension-api';
import { openLumiaClient } from '$technical/api/lumia-session';
import { t } from '$technical/i18n/i18n';
import { savePage } from '$domain/save/save-page';
import { NEEDS_SETTINGS, OUTCOME_MESSAGE, showOutcomeBadge } from '$domain/save/save-feedback';

export const SAVE_LINK_MENU_ID = 'save-link';
export const SAVE_PAGE_COMMAND = 'save-page';

export function createSaveAndNotify(extension: ExtensionApi) {
	return async function saveAndNotify(url: string | undefined): Promise<void> {
		const client = await openLumiaClient(extension.storage.local);
		const outcome = await savePage(client, url);
		await showOutcomeBadge(extension.action, outcome, t(OUTCOME_MESSAGE[outcome]));
		if (NEEDS_SETTINGS.has(outcome)) await extension.runtime.openOptionsPage();
	};
}

export function registerBackground(extension: ExtensionApi): void {
	const saveAndNotify = createSaveAndNotify(extension);

	extension.runtime.onInstalled.addListener(() => {
		extension.contextMenus.create({
			id: SAVE_LINK_MENU_ID,
			title: t('menu.saveLink'),
			contexts: ['link']
		});
	});

	extension.contextMenus.onClicked.addListener((info) => {
		if (info.menuItemId === SAVE_LINK_MENU_ID) void saveAndNotify(info.linkUrl);
	});

	extension.commands.onCommand.addListener((command) => {
		if (command !== SAVE_PAGE_COMMAND) return;
		void extension.tabs
			.query({ active: true, currentWindow: true })
			.then(([tab]) => saveAndNotify(tab?.url));
	});
}
