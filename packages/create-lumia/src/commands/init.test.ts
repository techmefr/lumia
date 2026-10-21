import { describe, expect, it } from "vitest";
import { parseEnv } from "../env-file.js";
import { createFakeEnvironment } from "../test-support/fake-environment.js";
import { InitError, runInit } from "./init.js";

const EXAMPLE =
	"POSTGRES_PASSWORD=change-me\nJWT_SECRET=change-me\nSECRET_ENCRYPTION_KEY=change-me\nMINIFLUX_PASSWORD=change-me\nMINIFLUX_WEBHOOK_SECRET=change-me\n# MINIFLUX_BASE_URL=https://miniflux.example.org\nFRONTEND_URL=http://localhost:8080\n";
const base = { dir: "/lumia", yes: true, force: false };
const checkout = () => createFakeEnvironment({ "/lumia/.env.example": EXAMPLE });
const written = (env: { files: Map<string, string> }) => env.files.get("/lumia/.env") ?? "";

describe("init", () => {
	it("writes .env from the example with generated secrets and the bundled default", async () => {
		const env = checkout();
		await runInit(base, env);
		const values = parseEnv(written(env));
		expect(values.get("POSTGRES_PASSWORD")).toMatch(/^[0-9a-f]{64}$/);
		expect(values.has("COMPOSE_FILE")).toBe(false);
	});

	it("never prints a secret", async () => {
		const env = checkout();
		await runInit(base, env);
		const secret = parseEnv(written(env)).get("JWT_SECRET") ?? "";
		expect(secret).not.toBe("");
		expect(env.logs.join("\n")).not.toContain(secret);
	});

	it("maps an external Miniflux to the override file and its address", async () => {
		const env = checkout();
		await runInit({ ...base, minifluxUrl: "https://rss.example.org/" }, env);
		const values = parseEnv(written(env));
		expect(values.get("MINIFLUX_BASE_URL")).toBe("https://rss.example.org");
		expect(values.get("COMPOSE_FILE")).toBe(
			"docker-compose.yml:docker-compose.external-miniflux.yml"
		);
		expect(values.get("MINIFLUX_PASSWORD")).toBe("change-me");
	});

	it("rejects an external Miniflux without a usable address", async () => {
		const env = checkout();
		await expect(runInit({ ...base, miniflux: "external" }, env)).rejects.toThrow(InitError);
		expect(env.files.has("/lumia/.env")).toBe(false);
	});

	it("refuses to replace an existing .env without --force when non-interactive", async () => {
		const env = createFakeEnvironment({ "/lumia/.env.example": EXAMPLE, "/lumia/.env": "KEEP=1" });
		await expect(runInit(base, env)).rejects.toThrow("--force");
		expect(written(env)).toBe("KEEP=1");
	});

	it("replaces an existing .env with --force", async () => {
		const env = createFakeEnvironment({ "/lumia/.env.example": EXAMPLE, "/lumia/.env": "KEEP=1" });
		await runInit({ ...base, force: true }, env);
		expect(written(env)).toContain("JWT_SECRET=");
	});

	it("asks before replacing and keeps the file on a no", async () => {
		const env = createFakeEnvironment({ "/lumia/.env.example": EXAMPLE, "/lumia/.env": "KEEP=1" });
		env.answers.confirm.push(false);
		expect(await runInit({ ...base, yes: false }, env)).toBe(false);
		expect(written(env)).toBe("KEEP=1");
	});

	it("prompts for the mode and the address when interactive", async () => {
		const env = checkout();
		env.answers.select.push("external");
		env.answers.text.push("https://rss.example.org");
		await runInit({ ...base, yes: false }, env);
		expect(written(env)).toContain("MINIFLUX_BASE_URL=https://rss.example.org");
	});

	it("fails outside a Lumia checkout", async () => {
		await expect(runInit(base, createFakeEnvironment())).rejects.toThrow("Lumia checkout");
	});
});
