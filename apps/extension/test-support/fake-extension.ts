import { vi } from 'vitest';
import type { ContextMenuClick, ExtensionApi, ExtensionTab } from '$technical/browser/extension-api';

interface FakeOptions {
	permissionGranted?: boolean;
	tabs?: ExtensionTab[];
	stored?: Record<string, unknown>;
	sidePanel?: boolean;
	sidebarAction?: boolean;
}

export function createFakeExtension(options: FakeOptions = {}) {
	const store: Record<string, unknown> = { ...options.stored };
	const badge = { text: '', color: '', title: '' };
	const menus: { id: string; title: string; contexts: string[] }[] = [];
	const permissionRequests: string[][] = [];
	let optionsPageOpened = 0;
	const panelOpens: string[] = [];
	let onInstalled: () => void = () => undefined;
	let onMenuClicked: (info: ContextMenuClick) => void = () => undefined;
	let onCommand: (command: string) => void = () => undefined;

	const extension: ExtensionApi = {
		storage: {
			local: {
				get: async (keys) => Object.fromEntries(keys.filter((key) => key in store).map((key) => [key, store[key]])),
				set: async (items) => {
					Object.assign(store, items);
				},
				remove: async (keys) => {
					for (const key of keys) delete store[key];
				}
			}
		},
		action: {
			setBadgeText: async ({ text }) => {
				badge.text = text;
			},
			setBadgeBackgroundColor: async ({ color }) => {
				badge.color = color;
			},
			setTitle: async ({ title }) => {
				badge.title = title;
			}
		},
		contextMenus: {
			create: (properties) => {
				menus.push(properties);
			},
			onClicked: { addListener: (listener) => (onMenuClicked = listener) }
		},
		commands: { onCommand: { addListener: (listener) => (onCommand = listener) } },
		runtime: {
			onInstalled: { addListener: (listener) => (onInstalled = listener) },
			openOptionsPage: async () => {
				optionsPageOpened += 1;
			}
		},
		tabs: { query: vi.fn(async () => options.tabs ?? []) },
		permissions: {
			request: async ({ origins }) => {
				permissionRequests.push(origins);
				return options.permissionGranted ?? true;
			}
		},
		...(options.sidePanel
			? {
					sidePanel: {
						open: async ({ windowId }: { windowId: number }) => {
							panelOpens.push(`sidePanel:${windowId}`);
						}
					}
				}
			: {}),
		...(options.sidebarAction
			? {
					sidebarAction: {
						open: async () => {
							panelOpens.push('sidebarAction');
						}
					}
				}
			: {})
	};

	return {
		extension,
		store,
		badge,
		menus,
		permissionRequests,
		panelOpens,
		optionsPageOpened: () => optionsPageOpened,
		fire: {
			installed: () => onInstalled(),
			menuClicked: (info: ContextMenuClick) => onMenuClicked(info),
			command: (name: string) => onCommand(name)
		}
	};
}
