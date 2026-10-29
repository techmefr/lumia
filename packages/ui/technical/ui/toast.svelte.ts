export interface ToastAction {
	label: string;
	run: () => void | Promise<void>;
}

export interface Toast {
	id: number;
	message: string;
	tone: 'default' | 'destructive';
	action?: ToastAction;
}

export interface ToastOptions {
	tone?: Toast['tone'];
	action?: ToastAction;
	/** Milliseconds before auto-dismiss. Toasts carrying an action get longer by default. */
	duration?: number;
}

const DEFAULT_DURATION = 3000;
const ACTION_DURATION = 7000;
/** A failure has to be read, and often acted on: it stays up longer than a confirmation. */
const ERROR_DURATION = 8000;

let nextId = 0;

class ToastStore {
	toasts = $state<Toast[]>([]);
	private timers = new Map<number, { handle: ReturnType<typeof setTimeout>; endsAt: number }>();
	private remaining = new Map<number, number>();

	private schedule(id: number, delay: number): void {
		const handle = setTimeout(() => this.dismiss(id), delay);
		this.timers.set(id, { handle, endsAt: Date.now() + delay });
	}

	pause(id: number): void {
		const timer = this.timers.get(id);
		if (!timer) return;
		clearTimeout(timer.handle);
		this.timers.delete(id);
		this.remaining.set(id, Math.max(timer.endsAt - Date.now(), 1000));
	}

	resume(id: number): void {
		const delay = this.remaining.get(id);
		if (delay === undefined || this.timers.has(id)) return;
		this.remaining.delete(id);
		this.schedule(id, delay);
	}

	show(message: string, options: ToastOptions = {}): number {
		const id = ++nextId;
		const toast: Toast = {
			id,
			message,
			tone: options.tone ?? 'default',
			action: options.action
		};
		this.toasts = [...this.toasts, toast];

		const fallback = options.action
			? ACTION_DURATION
			: toast.tone === 'destructive'
				? ERROR_DURATION
				: DEFAULT_DURATION;
		this.schedule(id, options.duration ?? fallback);
		return id;
	}

	dismiss(id: number): void {
		const timer = this.timers.get(id);
		if (timer) clearTimeout(timer.handle);
		this.timers.delete(id);
		this.remaining.delete(id);
		this.toasts = this.toasts.filter((toast) => toast.id !== id);
	}
}

export const toasts = new ToastStore();

export function toast(message: string, options?: ToastOptions): number {
	return toasts.show(message, options);
}
