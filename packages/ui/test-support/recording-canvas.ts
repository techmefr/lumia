import { vi } from 'vitest';

export interface DrawnLine {
	from: [number, number];
	to: [number, number];
	color: string;
	width: number;
}

export interface CanvasRecording {
	lines: DrawnLine[];
	clears: number;
}

/**
 * jsdom has no 2d context at all — `getContext` throws "not implemented" and returns null — so a
 * canvas component is untestable past its markup without one. This records the drawing calls
 * instead of rasterising them, which is what a test wants anyway: the strokes are the component's
 * observable output, and pixels would only have to be decoded back into them.
 */
export function recordingCanvasContext(): CanvasRecording {
	const recording: CanvasRecording = { lines: [], clears: 0 };
	let pen: [number, number] = [0, 0];
	let start: [number, number] = [0, 0];

	const context = {
		strokeStyle: '',
		lineWidth: 0,
		clearRect: () => {
			recording.clears += 1;
		},
		beginPath: () => {},
		moveTo: (x: number, y: number) => {
			start = [x, y];
			pen = [x, y];
		},
		lineTo: (x: number, y: number) => {
			pen = [x, y];
		},
		stroke: () => {
			recording.lines.push({
				from: start,
				to: pen,
				color: String(context.strokeStyle),
				width: Number(context.lineWidth)
			});
		}
	};

	vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
		context as unknown as CanvasRenderingContext2D
	);

	return recording;
}

/**
 * A hand-cranked animation loop. The component drives itself off requestAnimationFrame, and a test
 * that let the real one run would be timing-dependent; stepping the frames by hand also lets the
 * timestamp be stated, which is what every spark's lifetime is measured against.
 */
export function manualFrames() {
	let pending: FrameRequestCallback | null = null;
	let cancelled = false;

	vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
		pending = callback;
		return 1;
	});
	vi.stubGlobal('cancelAnimationFrame', () => {
		cancelled = true;
		pending = null;
	});

	return {
		/** Runs one frame at the given timestamp, in milliseconds since the run started. */
		step(timestamp: number) {
			const callback = pending;
			pending = null;
			callback?.(timestamp);
		},
		get running() {
			return pending !== null;
		},
		get cancelled() {
			return cancelled;
		}
	};
}
