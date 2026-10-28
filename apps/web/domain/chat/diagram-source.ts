const FENCE = /```mermaid[^\S\n]*\n([\s\S]*?)```/i;

export function diagramSource(content: string): string | null {
	const source = FENCE.exec(content)?.[1]?.trim();
	return source ? source : null;
}
