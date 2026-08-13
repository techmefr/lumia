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

let nextId = 0;

class ToastStore {
	toasts = $state<Toast[]>([]);

	show(message: string, options: ToastOptions = {}): number {
		const id = ++nextId;
		const toast: Toast = {
			id,
			message,
			tone: options.tone ?? 'default',
			action: options.action
		};
		this.toasts = [...this.toasts, toast];

		const duration = options.duration ?? (options.action ? ACTION_DURATION : DEFAULT_DURATION);
		setTimeout(() => this.dismiss(id), duration);
		return id;
	}

	dismiss(id: number): void {
		this.toasts = this.toasts.filter((toast) => toast.id !== id);
	}
}

export const toasts = new ToastStore();

export function toast(message: string, options?: ToastOptions): number {
	return toasts.show(message, options);
}
