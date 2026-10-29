export interface StorageArea {
	get(keys: string[]): Promise<Record<string, unknown>>;
	set(items: Record<string, unknown>): Promise<void>;
	remove(keys: string[]): Promise<void>;
	onChanged?: ExtensionEvent<(changes: Record<string, { newValue?: unknown }>) => void>;
}

export interface ExtensionEvent<Listener> {
	addListener(listener: Listener): void;
}

export interface ExtensionTab {
	id?: number;
	url?: string;
}

export interface ContextMenuClick {
	menuItemId: string | number;
	linkUrl?: string;
}

export interface ExtensionApi {
	storage: { local: StorageArea };
	action: {
		setBadgeText(details: { text: string; tabId?: number }): Promise<void>;
		setBadgeBackgroundColor(details: { color: string; tabId?: number }): Promise<void>;
		setTitle(details: { title: string; tabId?: number }): Promise<void>;
	};
	contextMenus: {
		create(properties: { id: string; title: string; contexts: string[] }): unknown;
		onClicked: ExtensionEvent<(info: ContextMenuClick) => void>;
	};
	commands: { onCommand: ExtensionEvent<(command: string) => void> };
	runtime: {
		onInstalled: ExtensionEvent<() => void>;
		openOptionsPage(): Promise<void>;
	};
	tabs: { query(query: { active: boolean; currentWindow: boolean }): Promise<ExtensionTab[]> };
	permissions: {
		request(permissions: { origins: string[] }): Promise<boolean>;
		remove(permissions: { origins: string[] }): Promise<boolean>;
	};
	sidePanel?: { open(options: { windowId: number }): Promise<void> };
	sidebarAction?: { open(): Promise<void> };
}

export function getExtension(): ExtensionApi {
	return chrome as unknown as ExtensionApi;
}
