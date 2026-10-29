export type ExtensionTarget = 'chrome' | 'firefox';

export function buildManifest(target: ExtensionTarget, version: string) {
	const background =
		target === 'firefox'
			? { scripts: ['background.js'], type: 'module' }
			: { service_worker: 'background.js', type: 'module' };

	const readerPanel =
		target === 'firefox'
			? {
					browser_specific_settings: {
						gecko: {
							id: 'lumia@techme.fr',
							data_collection_permissions: { required: ['none'] }
						}
					},
					sidebar_action: {
						default_title: '__MSG_extensionName__',
						default_panel: 'sidepanel/index.html',
						open_at_install: false
					}
				}
			: { side_panel: { default_path: 'sidepanel/index.html' } };

	return {
		manifest_version: 3,
		name: '__MSG_extensionName__',
		description: '__MSG_extensionDescription__',
		version,
		...(target === 'chrome' ? { minimum_chrome_version: '114' } : {}),
		icons: { '48': 'icons/icon-48.png', '96': 'icons/icon-96.png', '192': 'icons/icon-192.png' },
		default_locale: 'en',
		permissions:
			target === 'chrome'
				? ['storage', 'activeTab', 'contextMenus', 'sidePanel']
				: ['storage', 'activeTab', 'contextMenus'],
		optional_host_permissions: ['http://*/*', 'https://*/*'],
		background,
		action: {
			default_title: '__MSG_extensionName__',
			default_popup: 'popup/index.html',
			default_icon: { '48': 'icons/icon-48.png', '96': 'icons/icon-96.png' }
		},
		options_ui: { page: 'options/index.html', open_in_tab: true },
		commands: {
			'save-page': {
				suggested_key: { default: 'Alt+Shift+L' },
				description: '__MSG_commandSavePage__'
			},
			'open-reader': {
				suggested_key: { default: 'Alt+Shift+K' },
				description: '__MSG_commandOpenReader__'
			}
		},
		...readerPanel
	};
}
