import { describe, expect, it } from "vitest";
import {
	composeArgs,
	composeFileVariable,
	composeFiles,
	detectMode,
	meetsMinimumCompose,
	parseComposeVersion,
	portsFor
} from "./compose.js";

describe("compose file selection", () => {
	it("uses only the base file with the bundled Miniflux", () => {
		expect(composeFiles("bundled")).toEqual(["docker-compose.yml"]);
		expect(composeFileVariable("bundled")).toBeUndefined();
	});

	it("adds the external override when Miniflux lives elsewhere", () => {
		expect(composeFiles("external")).toEqual([
			"docker-compose.yml",
			"docker-compose.external-miniflux.yml"
		]);
		expect(composeFileVariable("external")).toBe(
			"docker-compose.yml:docker-compose.external-miniflux.yml"
		);
	});

	it("passes every file with -f before the subcommand", () => {
		expect(composeArgs("external", ["up", "-d"])).toEqual([
			"compose",
			"-f",
			"docker-compose.yml",
			"-f",
			"docker-compose.external-miniflux.yml",
			"up",
			"-d"
		]);
	});

	it("reads the mode back from COMPOSE_FILE", () => {
		const external = new Map([
			["COMPOSE_FILE", "docker-compose.yml:docker-compose.external-miniflux.yml"]
		]);
		expect(detectMode(external)).toBe("external");
		expect(detectMode(new Map())).toBe("bundled");
	});
});

describe("published ports", () => {
	it("leaves the Miniflux port out when Miniflux is external", () => {
		expect(portsFor("external").map((entry) => entry.port)).toEqual([8080, 8000]);
		expect(portsFor("bundled").map((entry) => entry.port)).toEqual([8080, 8000, 8090]);
	});
});

describe("compose version", () => {
	it("extracts the version from docker compose output", () => {
		expect(parseComposeVersion("Docker Compose version v2.29.1")).toEqual([2, 29, 1]);
		expect(parseComposeVersion("nothing")).toBeUndefined();
	});

	it("requires 2.24 for the !override tag", () => {
		expect(meetsMinimumCompose([2, 24, 0])).toBe(true);
		expect(meetsMinimumCompose([2, 23, 9])).toBe(false);
		expect(meetsMinimumCompose([3, 0, 0])).toBe(true);
		expect(meetsMinimumCompose([1, 29, 2])).toBe(false);
	});
});
