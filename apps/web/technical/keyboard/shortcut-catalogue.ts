/**
 * The single declaration of every shortcut the app answers to.
 *
 * Both the help panel and the hint under the article list are rendered from this table, so a key
 * can never be documented in one place and bound to something else in another.
 */

import type { MessageKey } from '$technical/i18n/i18n.svelte.js';

export interface ShortcutEntry {
	id: string;
	/** Rendered one `<kbd>` per element: `['g', 'a']` is a sequence, `['j', 'k']` an alternative. */
	keys: string[];
	labelKey: MessageKey;
}

export interface NavigationShortcut extends ShortcutEntry {
	key: string;
	href: string;
}

/**
 * Navigation is reached through a `g` prefix rather than a bare letter, for two reasons: the list
 * screens already spend most single letters on reading actions, and a two-key sequence leaves the
 * remaining letters free for the screen reader commands that expect to own them.
 */
export const NAVIGATION_PREFIX = 'g';

export const NAVIGATION_SHORTCUTS: NavigationShortcut[] = [
	{ id: 'articles', key: 'a', href: '/articles', keys: ['g', 'a'], labelKey: 'nav.articles' },
	{ id: 'etincelle', key: 'e', href: '/etincelle', keys: ['g', 'e'], labelKey: 'nav.etincelle' },
	{ id: 'feeds', key: 'f', href: '/feeds', keys: ['g', 'f'], labelKey: 'nav.feeds' },
	{
		id: 'read-later',
		key: 'l',
		href: '/a-lire-plus-tard',
		keys: ['g', 'l'],
		labelKey: 'nav.readLater'
	},
	{ id: 'playlists', key: 'p', href: '/playlists', keys: ['g', 'p'], labelKey: 'nav.playlists' },
	{ id: 'favorites', key: 'v', href: '/favoris', keys: ['g', 'v'], labelKey: 'nav.favorites' },
	{ id: 'settings', key: 's', href: '/settings', keys: ['g', 's'], labelKey: 'nav.settings' }
];

/** Bound by the article list screen, and only live while it is on screen. */
export const READING_SHORTCUTS: ShortcutEntry[] = [
	{ id: 'move', keys: ['j', 'k'], labelKey: 'articles.shortcutNavigate' },
	{ id: 'open', keys: ['o'], labelKey: 'articles.shortcutOpen' },
	{ id: 'read', keys: ['m'], labelKey: 'articles.shortcutRead' },
	{ id: 'save', keys: ['s'], labelKey: 'articles.shortcutSave' },
	{ id: 'unread', keys: ['u'], labelKey: 'articles.shortcutUnread' },
	{ id: 'flip', keys: ['f'], labelKey: 'articles.shortcutFlip' },
	{ id: 'search', keys: ['/'], labelKey: 'articles.shortcutSearch' },
	{ id: 'select', keys: ['x'], labelKey: 'articles.shortcutSelect' },
	{ id: 'extend', keys: ['shift+j', 'shift+k'], labelKey: 'articles.shortcutExtend' },
	{ id: 'select-all', keys: ['shift+a'], labelKey: 'articles.shortcutSelectAll' }
];

export const HELP_SHORTCUTS: ShortcutEntry[] = [
	{ id: 'help', keys: ['?'], labelKey: 'shortcuts.help' }
];
