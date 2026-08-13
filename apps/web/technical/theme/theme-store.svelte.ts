const STORAGE_KEY = 'lumia-theme';

export type Theme = 'light' | 'dark';

function readInitialTheme(): Theme {
	if (typeof document === 'undefined') return 'light';
	return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

let theme = $state<Theme>(readInitialTheme());

function apply(next: Theme) {
	theme = next;
	document.documentElement.classList.toggle('dark', next === 'dark');
	localStorage.setItem(STORAGE_KEY, next);
}

export function getTheme(): Theme {
	return theme;
}

export function toggleTheme(): void {
	apply(theme === 'dark' ? 'light' : 'dark');
}
