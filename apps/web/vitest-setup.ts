import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';

// Every store in the app reads its initial value from localStorage, so a test that writes one
// would otherwise decide what the next test sees.
afterEach(() => {
	localStorage.clear();
	document.documentElement.lang = '';
	document.documentElement.dir = '';
});
