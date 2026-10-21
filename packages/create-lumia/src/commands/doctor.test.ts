import { describe, expect, it } from "vitest";
import { createFakeEnvironment, type FakeEnvironment } from "../test-support/fake-environment.js";
import { isHealthy, runDoctor } from "./doctor.js";

const GOOD_ENV =
	"POSTGRES_PASSWORD=a\nJWT_SECRET=a\nSECRET_ENCRYPTION_KEY=a\nMINIFLUX_WEBHOOK_SECRET=a\nMINIFLUX_PASSWORD=a\nMINIFLUX_USERNAME=admin\n";

const healthy = (initial: Record<string, string> = { "/lumia/.env": GOOD_ENV }): FakeEnvironment => {
	const env = createFakeEnvironment(initial);
	env.capturedResults.set("docker --version", { code: 0, stdout: "Docker version 27.0.0" });
	env.capturedResults.set("docker compose version", {
		code: 0,
		stdout: "Docker Compose version v2.29.1"
	});
	return env;
};

const statusOf = (checks: { name: string; status: string }[], name: string) =>
	checks.find((check) => check.name === name)?.status;

describe("doctor", () => {
	it("passes on a ready machine", async () => {
		expect(isHealthy(await runDoctor({ dir: "/lumia" }, healthy()))).toBe(true);
	});

	it("fails when docker is missing", async () => {
		const env = createFakeEnvironment({ "/lumia/.env": GOOD_ENV });
		const checks = await runDoctor({ dir: "/lumia" }, env);
		expect(statusOf(checks, "docker")).toBe("fail");
		expect(isHealthy(checks)).toBe(false);
	});

	it("fails on a compose version without the !override tag", async () => {
		const env = healthy();
		env.capturedResults.set("docker compose version", {
			code: 0,
			stdout: "Docker Compose version v2.20.0"
		});
		expect(statusOf(await runDoctor({ dir: "/lumia" }, env), "compose")).toBe("fail");
	});

	it("warns, without failing, when a port is taken", async () => {
		const env = healthy();
		env.busyPorts.add(8080);
		const checks = await runDoctor({ dir: "/lumia" }, env);
		expect(statusOf(checks, "port 8080")).toBe("warn");
		expect(isHealthy(checks)).toBe(true);
	});

	it("fails when .env is absent", async () => {
		expect(statusOf(await runDoctor({ dir: "/lumia" }, healthy({})), ".env")).toBe("fail");
	});

	it("names the keys that are unset", async () => {
		const env = healthy({ "/lumia/.env": "JWT_SECRET=change-me\n" });
		await runDoctor({ dir: "/lumia" }, env);
		expect(env.logs.join("\n")).toContain("JWT_SECRET");
	});

	it("checks the Miniflux address in external mode and skips port 8090", async () => {
		const external = `${GOOD_ENV}COMPOSE_FILE=docker-compose.yml:docker-compose.external-miniflux.yml\nMINIFLUX_BASE_URL=https://rss.example.org\n`;
		const env = healthy({ "/lumia/.env": external });
		env.unreachable.add("https://rss.example.org");
		const checks = await runDoctor({ dir: "/lumia" }, env);
		expect(statusOf(checks, "miniflux")).toBe("fail");
		expect(statusOf(checks, "port 8090")).toBeUndefined();
	});

	it("passes the external check when Miniflux answers", async () => {
		const external = `${GOOD_ENV}MINIFLUX_BASE_URL=https://rss.example.org\n`;
		const checks = await runDoctor(
			{ dir: "/lumia", miniflux: "external" },
			healthy({ "/lumia/.env": external })
		);
		expect(statusOf(checks, "miniflux")).toBe("ok");
	});

	it("fails the external check when the address is not set", async () => {
		const checks = await runDoctor({ dir: "/lumia", miniflux: "external" }, healthy());
		expect(statusOf(checks, "miniflux")).toBe("fail");
	});
});
