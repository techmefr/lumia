import { resolve } from "node:path";
import { runCommand } from "citty";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createCli, parseMode } from "./cli.js";
import { createFakeEnvironment, type FakeEnvironment } from "./test-support/fake-environment.js";

describe("parseMode", () => {
	it("accepts the two modes and an absent flag", () => {
		expect(parseMode("bundled")).toBe("bundled");
		expect(parseMode("external")).toBe("external");
		expect(parseMode(undefined)).toBeUndefined();
	});

	it("rejects anything else", () => {
		expect(() => parseMode("hosted")).toThrow("--miniflux");
	});
});

describe("createCli", () => {
	const dir = resolve("/lumia-project");
	const envPath = `${dir}/.env`;
	let previousExitCode: typeof process.exitCode;

	beforeEach(() => {
		previousExitCode = process.exitCode;
		process.exitCode = undefined;
	});

	afterEach(() => {
		process.exitCode = previousExitCode;
	});

	const run = (env: FakeEnvironment, ...rawArgs: string[]) =>
		runCommand(createCli(env), { rawArgs });

	it("init writes the .env from the flags", async () => {
		const env = createFakeEnvironment({ [`${dir}/.env.example`]: "APP_KEY=\n" });
		await run(env, "init", dir, "--yes", "--miniflux", "bundled", "--frontend-url", "http://x.test");
		expect(env.files.has(envPath)).toBe(true);
		expect(process.exitCode).toBeUndefined();
	});

	it("init reports a failure and sets the exit code", async () => {
		const env = createFakeEnvironment({ [envPath]: "A=1\n", [`${dir}/.env.example`]: "A=\n" });
		await run(env, "init", dir, "--yes");
		expect(process.exitCode).toBe(1);
		expect(env.logs.some((line) => line.startsWith("error"))).toBe(true);
	});

	it("rejects an invalid miniflux mode through the guard", async () => {
		const env = createFakeEnvironment({ [`${dir}/.env.example`]: "A=\n" });
		await run(env, "init", dir, "--yes", "--miniflux", "hosted");
		expect(process.exitCode).toBe(1);
		expect(env.logs.join("\n")).toContain("--miniflux");
	});

	it("doctor sets a failing exit code when a check fails", async () => {
		const env = createFakeEnvironment();
		await run(env, "doctor", dir);
		expect(process.exitCode).toBe(1);
	});

	it("up fails when .env is missing", async () => {
		const env = createFakeEnvironment();
		await run(env, "up", dir);
		expect(process.exitCode).toBe(1);
		expect(env.streamed).toHaveLength(0);
	});

	it("up starts docker compose detached, or attached with --foreground", async () => {
		const env = createFakeEnvironment({ [envPath]: "MINIFLUX_MODE=bundled\n" });
		await run(env, "up", dir, "--miniflux", "bundled");
		await run(env, "up", dir, "--miniflux", "bundled", "--foreground");
		expect(env.streamed[0]?.args).toContain("-d");
		expect(env.streamed[1]?.args).not.toContain("-d");
	});

	it("up propagates a non-zero compose exit code", async () => {
		const env = createFakeEnvironment({ [envPath]: "A=1\n" });
		env.streamCode = 3;
		await run(env, "up", dir, "--miniflux", "external");
		expect(process.exitCode).toBe(3);
	});

	it("rethrows unexpected errors", async () => {
		const env = createFakeEnvironment({ [envPath]: "A=1\n" });
		env.shell.stream = async () => {
			throw new TypeError("boom");
		};
		await expect(run(env, "up", dir, "--miniflux", "bundled")).rejects.toThrow("boom");
	});
});
