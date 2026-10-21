import type { MinifluxMode } from "./types.js";

const SECRET_BYTES = 32;
const FERNET_KEY_LENGTH = 44;

export const PLACEHOLDER = "change-me";

export const REQUIRED_KEYS = [
	"POSTGRES_PASSWORD",
	"JWT_SECRET",
	"SECRET_ENCRYPTION_KEY",
	"MINIFLUX_WEBHOOK_SECRET",
	"MINIFLUX_PASSWORD"
] as const;

type RandomBytes = (size: number) => Buffer;

export const generateSecret = (randomBytes: RandomBytes): string =>
	randomBytes(SECRET_BYTES).toString("hex");

export const generateFernetKey = (randomBytes: RandomBytes): string =>
	randomBytes(SECRET_BYTES).toString("base64url").padEnd(FERNET_KEY_LENGTH, "=");

export const parseEnv = (content: string): Map<string, string> => {
	const entries = new Map<string, string>();
	for (const line of content.split(/\r?\n/)) {
		const match = /^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/.exec(line);
		if (match?.[1] !== undefined) entries.set(match[1], match[2] ?? "");
	}
	return entries;
};

export const applyValues = (template: string, values: Record<string, string>): string => {
	const pending = new Map(Object.entries(values));
	const lines = template.split(/\r?\n/).map((line) => {
		const key = /^(?:#\s*)?([A-Za-z_][A-Za-z0-9_]*)=/.exec(line)?.[1];
		if (key === undefined || !pending.has(key)) return line;
		const value = pending.get(key);
		pending.delete(key);
		return `${key}=${value}`;
	});
	const appended = [...pending].map(([key, value]) => `${key}=${value}`);
	if (appended.length === 0) return lines.join("\n");
	const body = lines.at(-1) === "" ? lines.slice(0, -1) : lines;
	return [...body, ...appended, ""].join("\n");
};

export interface EnvPlan {
	mode: MinifluxMode;
	minifluxBaseUrl?: string;
	frontendUrl?: string;
	composeFile?: string;
	randomBytes: RandomBytes;
}

export const buildEnvValues = (plan: EnvPlan): Record<string, string> => {
	const values: Record<string, string> = {
		POSTGRES_PASSWORD: generateSecret(plan.randomBytes),
		JWT_SECRET: generateSecret(plan.randomBytes),
		SECRET_ENCRYPTION_KEY: generateFernetKey(plan.randomBytes),
		MINIFLUX_WEBHOOK_SECRET: generateSecret(plan.randomBytes)
	};
	if (plan.mode === "bundled") values.MINIFLUX_PASSWORD = generateSecret(plan.randomBytes);
	if (plan.mode === "external" && plan.minifluxBaseUrl !== undefined) {
		values.MINIFLUX_BASE_URL = plan.minifluxBaseUrl;
	}
	if (plan.frontendUrl !== undefined) values.FRONTEND_URL = plan.frontendUrl;
	if (plan.composeFile !== undefined) values.COMPOSE_FILE = plan.composeFile;
	return values;
};

export const missingKeys = (env: Map<string, string>, mode: MinifluxMode): string[] => {
	const required: string[] = [...REQUIRED_KEYS];
	if (mode === "external") required.push("MINIFLUX_BASE_URL", "MINIFLUX_USERNAME");
	return required.filter((key) => {
		const value = env.get(key);
		return value === undefined || value === "" || value === PLACEHOLDER;
	});
};
