import { render, waitFor } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { setLocale } from '$technical/i18n/i18n.svelte';
import MermaidDiagram from './mermaid-diagram.svelte';

const mermaid = vi.hoisted(() => ({ initialize: vi.fn(), render: vi.fn() }));

vi.mock('mermaid', () => ({ default: mermaid }));

type Props = Parameters<typeof MermaidDiagram>[1];

beforeEach(() => {
	setLocale('en');
	vi.clearAllMocks();
});

describe('the mermaid diagram', () => {
	it('draws the source with the strict security level', async () => {
		mermaid.render.mockResolvedValue({ svg: '<svg data-test-drawn></svg>' });
		const { container } = render(MermaidDiagram, { source: 'graph LR\n A --> B' } as Props);

		await waitFor(() => expect(container.querySelector('[data-test-chat-diagram] svg')).not.toBeNull());
		expect(mermaid.initialize).toHaveBeenCalledWith(
			expect.objectContaining({ securityLevel: 'strict', startOnLoad: false })
		);
		expect(mermaid.render).toHaveBeenCalledWith(expect.any(String), 'graph LR\n A --> B');
	});

	it('falls back to the source and an alert when the diagram cannot be drawn', async () => {
		mermaid.render.mockRejectedValue(new Error('parse error'));
		const { container } = render(MermaidDiagram, { source: 'not a diagram' } as Props);

		await waitFor(() =>
			expect(container.querySelector('[data-test-chat-diagram-failed] [role="alert"]')).not.toBeNull()
		);
		expect(container.querySelector('pre')?.textContent).toBe('not a diagram');
		expect(container.querySelector('[data-test-chat-diagram]')).toBeNull();
	});
});
