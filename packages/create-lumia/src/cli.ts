import { resolve } from "node:path";
import { defineCommand } from "citty";
import { isHealthy, runDoctor } from "./commands/doctor.js";
import { InitError, runInit } from "./commands/init.js";
import { UpError, runUp } from "./commands/up.js";
import type { Environment, MinifluxMode } from "./types.js";

export const parseMode = (value: unknown): MinifluxMode | undefined => {
	if (value === undefined) return undefined;
	if (value === "bundled" || value === "external") return value;
	throw new InitError(`--miniflux must be "bundled" or "external", got "${String(value)}"`);
};

const directory = {
	type: "positional",
	required: false,
	default: ".",
	description: "Lumia checkout"
} as const;
const minifluxFlag = { type: "string", description: "bundled or external" } as const;

const text = (value: unknown): string | undefined => (typeof value === "string" ? value : undefined);
const flag = (value: unknown): boolean => value === true;
const target = (value: unknown): string => resolve(text(value) ?? ".");

const guarded =async (env: Environment, action: () => Promise<number | void>): Promise<void> => {
	try {
		const code = await action();
		if (typeof code === "number" && code !== 0) process.exitCode = code;
	} catch (error) {
		if (!(error instanceof InitError || error instanceof UpError)) throw error;
		env.logger.error(error.message);
		process.exitCode = 1;
	}
};

export const createCli = (env: Environment) =>
	defineCommand({
		meta: {
			name: "create-lumia",
			description: "Set up, check and start a self-hosted Lumia instance"
		},
		subCommands: {
			init: defineCommand({
				meta: { name: "init", description: "Write .env with generated secrets" },
				args: {
					dir: directory,
					miniflux: minifluxFlag,
					"miniflux-url": { type: "string", description: "Address of an external Miniflux" },
					"frontend-url": { type: "string", description: "Public address of the web app" },
					yes: { type: "boolean", description: "Never prompt, use flags and defaults" },
					force: { type: "boolean", description: "Replace an existing .env" }
				},
				run: ({ args }) =>
					guarded(env, async () => {
						await runInit(
							{
								dir: target(args.dir),
								miniflux: parseMode(args.miniflux),
								minifluxUrl: text(args["miniflux-url"]),
								frontendUrl: text(args["frontend-url"]),
								yes: flag(args.yes),
								force: flag(args.force)
							},
							env
						);
					})
			}),
			doctor: defineCommand({
				meta: { name: "doctor", description: "Check docker, ports and .env" },
				args: { dir: directory, miniflux: minifluxFlag },
				run: ({ args }) =>
					guarded(env, async () => {
						const checks = await runDoctor(
							{ dir: target(args.dir), miniflux: parseMode(args.miniflux) },
							env
						);
						return isHealthy(checks) ? 0 : 1;
					})
			}),
			up: defineCommand({
				meta: { name: "up", description: "Start Lumia with docker compose" },
				args: {
					dir: directory,
					miniflux: minifluxFlag,
					foreground: { type: "boolean", description: "Stay attached instead of detaching" }
				},
				run: ({ args }) =>
					guarded(env, () =>
						runUp(
							{
								dir: target(args.dir),
								miniflux: parseMode(args.miniflux),
								foreground: flag(args.foreground)
							},
							env
						)
					)
			})
		}
	});
