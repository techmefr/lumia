import { cleanup, fireEvent, render } from '@testing-library/svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import InstanceUrlForm from './instance-url-form.svelte';

vi.mock('$technical/api/client', () => ({ apiBaseUrl: '' }));

afterEach(() => {
	cleanup();
	localStorage.clear();
});

function form() {
	const { container } = render(InstanceUrlForm);
	const q = <T extends Element>(selector: string) => container.querySelector<T>(selector);
	return {
		input: () => q<HTMLInputElement>('[data-test-instance-url]')!,
		form: () => q<HTMLFormElement>('[data-test-instance-form]')!,
		insecure: () => q('[data-test-instance-insecure]'),
		host: () => q('[data-test-instance-host]')
	};
}

describe('the instance address form', () => {
	it('refuses plain http on a remote host and stores nothing', async () => {
		const view = form();

		await fireEvent.input(view.input(), { target: { value: 'http://lumia.example.com/api' } });
		await fireEvent.submit(view.form());

		expect(view.insecure()).not.toBeNull();
		expect(localStorage.getItem('lumia-instance-url')).toBeNull();
	});

	it('shows the host the app is about to talk to', async () => {
		const view = form();

		await fireEvent.input(view.input(), { target: { value: 'https://lumia.example.com/api' } });

		expect(view.host()?.textContent).toContain('lumia.example.com');
	});
});
