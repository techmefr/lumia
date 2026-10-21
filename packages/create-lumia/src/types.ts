export type MinifluxMode = "bundled" | "external";

export interface FileSystem {
	exists(path: string): Promise<boolean>;
	read(path: string): Promise<string>;
	write(path: string, content: string): Promise<void>;
}

export interface CommandResult {
	code: number;
	stdout: string;
}

export interface Shell {
	capture(command: string, args: string[], cwd?: string): Promise<CommandResult>;
	stream(command: string, args: string[], cwd: string): Promise<number>;
}

export interface Network {
	isPortFree(port: number): Promise<boolean>;
	isReachable(url: string): Promise<boolean>;
}

export interface Prompter {
	confirm(message: string): Promise<boolean>;
	text(message: string, initial: string): Promise<string>;
	select<T extends string>(message: string, options: { label: string; value: T }[]): Promise<T>;
}

export interface Logger {
	info(message: string): void;
	success(message: string): void;
	warn(message: string): void;
	error(message: string): void;
}

export interface Environment {
	fs: FileSystem;
	shell: Shell;
	network: Network;
	prompter: Prompter;
	logger: Logger;
	randomBytes(size: number): Buffer;
	join(...parts: string[]): string;
}
