import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";
import { access, readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:net";
import { join } from "node:path";
import { consola } from "consola";
import type { Environment, Prompter } from "../types.js";

const REACHABILITY_TIMEOUT_MS = 5000;
const OWNER_ONLY = 0o600;

const answered = <T>(value: T | symbol): T => {
	if (typeof value === "symbol") throw new Error("Cancelled");
	return value;
};

const prompter: Prompter = {
	confirm: async (message) => answered(await consola.prompt(message, { type: "confirm" })),
	text: async (message, initial) =>
		answered(await consola.prompt(message, { type: "text", default: initial })),
	select: async <T extends string>(message: string, options: { label: string; value: T }[]) =>
		answered(
			(await consola.prompt(message, {
				type: "select",
				options: options.map(({ label, value }) => ({ label, value }))
			})) as unknown as T | symbol
		)
};

export const createNodeEnvironment = (): Environment => ({
	fs: {
		exists: (path) =>
			access(path).then(
				() => true,
				() => false
			),
		read: (path) => readFile(path, "utf8"),
		write: (path, content) => writeFile(path, content, { encoding: "utf8", mode: OWNER_ONLY })
	},
	shell: {
		capture: (command, args, cwd) =>
			new Promise((resolve) => {
				const child = spawn(command, args, { cwd, stdio: ["ignore", "pipe", "ignore"] });
				let stdout = "";
				child.stdout.on("data", (chunk: Buffer) => (stdout += chunk.toString()));
				child.on("error", () => resolve({ code: 127, stdout: "" }));
				child.on("close", (code) => resolve({ code: code ?? 1, stdout }));
			}),
		stream: (command, args, cwd) =>
			new Promise((resolve) => {
				const child = spawn(command, args, { cwd, stdio: "inherit" });
				child.on("error", () => resolve(127));
				child.on("close", (code) => resolve(code ?? 1));
			})
	},
	network: {
		isPortFree: (port) =>
			new Promise((resolve) => {
				const server = createServer();
				server.once("error", () => resolve(false));
				server.listen(port, () => server.close(() => resolve(true)));
			}),
		isReachable: async (url) => {
			try {
				await fetch(url, { signal: AbortSignal.timeout(REACHABILITY_TIMEOUT_MS) });
				return true;
			} catch {
				return false;
			}
		}
	},
	prompter,
	logger: {
		info: (message) => consola.info(message),
		success: (message) => consola.success(message),
		warn: (message) => consola.warn(message),
		error: (message) => consola.error(message)
	},
	randomBytes,
	join
});
