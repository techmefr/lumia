import { describe, expect, it } from 'vitest';
import { diagramSource } from './diagram-source';

describe('diagramSource', () => {
	it('extracts the source of a fenced mermaid block', () => {
		expect(diagramSource('```mermaid\nflowchart TD\n  A --> B\n```')).toBe('flowchart TD\n  A --> B');
	});

	it('finds the block inside surrounding prose', () => {
		expect(diagramSource('Here it is:\n```mermaid\ngraph LR\n  A --> B\n```\nDone.')).toBe(
			'graph LR\n  A --> B'
		);
	});

	it('ignores a fenced block of another language', () => {
		expect(diagramSource('```js\nconsole.log(1)\n```')).toBeNull();
	});

	it('ignores an empty block and plain text', () => {
		expect(diagramSource('```mermaid\n\n```')).toBeNull();
		expect(diagramSource('No diagram here.')).toBeNull();
	});
});
