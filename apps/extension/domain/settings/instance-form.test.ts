import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { createFakeExtension } from '$test-support/fake-extension';
import { en } from '$technical/i18n/messages/en';
import InstanceForm from './instance-form.svelte';

async function submit(address: string) {
	const field = screen.getByLabelText(en['settings.instanceLabel']);
	await userEvent.clear(field);
	await userEvent.type(field, address);
	await userEvent.click(screen.getByRole('button', { name: en['settings.instanceSave'] }));
}

describe('InstanceForm', () => {
	it('asks for access to the instance origin, then stores the normalised address', async () => {
		const fake = createFakeExtension();
		const onsaved = vi.fn();
		render(InstanceForm, { extension: fake.extension, onsaved });

		await submit('https://lumia.example.com/');

		expect(fake.permissionRequests).toEqual([['https://lumia.example.com/*']]);
		expect(fake.store['lumia.instance_url']).toBe('https://lumia.example.com');
		expect(onsaved).toHaveBeenCalledWith('https://lumia.example.com');
		expect(await screen.findByText(en['settings.instanceSaved'])).toBeInTheDocument();
	});

	it('starts from the address already stored', () => {
		const fake = createFakeExtension();
		render(InstanceForm, { extension: fake.extension, value: 'https://stored.example.com', onsaved: vi.fn() });
		expect(screen.getByLabelText(en['settings.instanceLabel'])).toHaveValue(
			'https://stored.example.com'
		);
	});

	it('rejects an address that is not http or https, without asking the browser for anything', async () => {
		const fake = createFakeExtension();
		const onsaved = vi.fn();
		render(InstanceForm, { extension: fake.extension, onsaved });

		await submit('ftp://lumia.example.com');

		expect(await screen.findByRole('alert')).toHaveTextContent(en['settings.instanceInvalid']);
		expect(fake.permissionRequests).toEqual([]);
		expect(fake.store).toEqual({});
		expect(onsaved).not.toHaveBeenCalled();
	});

	it('stores nothing when the browser refuses access to the address', async () => {
		const fake = createFakeExtension({ permissionGranted: false });
		const onsaved = vi.fn();
		render(InstanceForm, { extension: fake.extension, onsaved });

		await submit('https://lumia.example.com');

		expect(await screen.findByRole('alert')).toHaveTextContent(en['settings.permissionDenied']);
		expect(fake.store).toEqual({});
		expect(onsaved).not.toHaveBeenCalled();
	});
});
