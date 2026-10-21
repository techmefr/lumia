import { describe, expect, it } from "vitest";
import { createFakeEnvironment } from "../test-support/fake-environment.js";
import { UpError, runUp } from "./up.js";

describe("up", () => {
	it("starts detached with the base file for a bundled Miniflux", async () => {
		const env = createFakeEnvironment({ "/lumia/.env": "A=1\n" });
		expect(await runUp({ dir: "/lumia", foreground: false }, env)).toBe(0);
		expect(env.streamed).toEqual([
			{ command: "docker", args: ["compose", "-f", "docker-compose.yml", "up", "-d"], cwd: "/lumia" }
		]);
	});

	it("adds the override file when .env selects the external Miniflux", async () => {
		const env = createFakeEnvironment({
			"/lumia/.env": "COMPOSE_FILE=docker-compose.yml:docker-compose.external-miniflux.yml\n"
		});
		await runUp({ dir: "/lumia", foreground: true }, env);
		expect(env.streamed[0]?.args).toEqual([
			"compose",
			"-f",
			"docker-compose.yml",
			"-f",
			"docker-compose.external-miniflux.yml",
			"up"
		]);
	});

	it("lets the flag win over .env", async () => {
		const env = createFakeEnvironment({ "/lumia/.env": "A=1\n" });
		await runUp({ dir: "/lumia", miniflux: "external", foreground: false }, env);
		expect(env.streamed[0]?.args).toContain("docker-compose.external-miniflux.yml");
	});

	it("returns the exit code of docker compose", async () => {
		const env = createFakeEnvironment({ "/lumia/.env": "A=1\n" });
		env.streamCode = 3;
		expect(await runUp({ dir: "/lumia", foreground: false }, env)).toBe(3);
		expect(env.logs.join("\n")).toContain("code 3");
	});

	it("refuses to start without .env", async () => {
		await expect(
			runUp({ dir: "/lumia", foreground: false }, createFakeEnvironment())
		).rejects.toThrow(UpError);
	});
});
