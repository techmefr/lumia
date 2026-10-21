import { describe, expect, it } from "vitest";
import { parseMode } from "./cli.js";

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
