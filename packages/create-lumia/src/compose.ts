import type { MinifluxMode } from "./types.js";

export const BASE_COMPOSE_FILE = "docker-compose.yml";
export const EXTERNAL_MINIFLUX_COMPOSE_FILE = "docker-compose.external-miniflux.yml";

export interface PublishedPort {
	port: number;
	service: string;
	mode: MinifluxMode | "any";
}

export const PUBLISHED_PORTS: PublishedPort[] = [
	{ port: 8080, service: "web", mode: "any" },
	{ port: 8000, service: "api", mode: "any" },
	{ port: 8090, service: "miniflux", mode: "bundled" }
];

export const composeFiles = (mode: MinifluxMode): string[] =>
	mode === "external" ? [BASE_COMPOSE_FILE, EXTERNAL_MINIFLUX_COMPOSE_FILE] : [BASE_COMPOSE_FILE];

export const composeFileVariable = (mode: MinifluxMode): string | undefined =>
	mode === "external" ? composeFiles(mode).join(":") : undefined;

export const composeArgs = (mode: MinifluxMode, subcommand: string[]): string[] => [
	"compose",
	...composeFiles(mode).flatMap((file) => ["-f", file]),
	...subcommand
];

export const detectMode = (env: Map<string, string>): MinifluxMode =>
	env.get("COMPOSE_FILE")?.split(":").includes(EXTERNAL_MINIFLUX_COMPOSE_FILE) === true
		? "external"
		: "bundled";

export const portsFor = (mode: MinifluxMode): PublishedPort[] =>
	PUBLISHED_PORTS.filter((entry) => entry.mode === "any" || entry.mode === mode);

const MINIMUM_COMPOSE = [2, 24, 0] as const;

export const parseComposeVersion = (output: string): number[] | undefined => {
	const match = /(\d+)\.(\d+)\.(\d+)/.exec(output);
	return match === null ? undefined : match.slice(1, 4).map(Number);
};

export const meetsMinimumCompose = (version: number[]): boolean => {
	for (const [index, required] of MINIMUM_COMPOSE.entries()) {
		const actual = version[index] ?? 0;
		if (actual !== required) return actual > required;
	}
	return true;
};
