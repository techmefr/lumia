import { describe, expect, it } from "vitest";
import {
	applyValues,
	buildEnvValues,
	generateFernetKey,
	generateSecret,
	missingKeys,
	parseEnv
} from "./env-file.js";

const counting = () => {
	let counter = 0;
	return (size: number) => Buffer.alloc(size, ++counter);
};

describe("secret generation", () => {
	it("produces 64 hex characters from 32 random bytes", () => {
		expect(generateSecret(() => Buffer.alloc(32, 255))).toBe("ff".repeat(32));
	});

	it("produces a padded url-safe base64 key that a Fernet reader accepts", () => {
		const key = generateFernetKey(() => Buffer.alloc(32, 251));
		expect(key).toHaveLength(44);
		expect(key).toMatch(/^[A-Za-z0-9_-]+=$/);
		expect(Buffer.from(key, "base64url")).toHaveLength(32);
	});
});

describe("applyValues", () => {
	const template = "A=change-me\n# B=old\nC=keep\n";

	it("replaces existing keys, uncomments commented ones and keeps the rest", () => {
		expect(applyValues(template, { A: "1", B: "2" })).toBe("A=1\nB=2\nC=keep\n");
	});

	it("appends keys the template does not mention", () => {
		expect(applyValues(template, { D: "4" })).toBe("A=change-me\n# B=old\nC=keep\nD=4\n");
	});
});

describe("buildEnvValues", () => {
	it("generates a distinct value for every secret", () => {
		const values = buildEnvValues({ mode: "bundled", randomBytes: counting() });
		const secrets = Object.values(values);
		expect(new Set(secrets).size).toBe(secrets.length);
		expect(values.MINIFLUX_PASSWORD).toBeDefined();
	});

	it("takes the Miniflux address and compose file for an external instance", () => {
		const values = buildEnvValues({
			mode: "external",
			minifluxBaseUrl: "https://rss.example.org",
			composeFile: "a:b",
			frontendUrl: "http://lan:8080",
			randomBytes: counting()
		});
		expect(values).toMatchObject({
			MINIFLUX_BASE_URL: "https://rss.example.org",
			COMPOSE_FILE: "a:b",
			FRONTEND_URL: "http://lan:8080"
		});
		expect(values.MINIFLUX_PASSWORD).toBeUndefined();
	});
});

describe("missingKeys", () => {
	it("flags empty, absent and placeholder values", () => {
		const env = parseEnv("POSTGRES_PASSWORD=change-me\nJWT_SECRET=\nSECRET_ENCRYPTION_KEY=x\n");
		expect(missingKeys(env, "bundled")).toEqual([
			"POSTGRES_PASSWORD",
			"JWT_SECRET",
			"MINIFLUX_WEBHOOK_SECRET",
			"MINIFLUX_PASSWORD"
		]);
	});

	it("also requires the Miniflux address and account when external", () => {
		const env = parseEnv(
			"POSTGRES_PASSWORD=a\nJWT_SECRET=a\nSECRET_ENCRYPTION_KEY=a\nMINIFLUX_WEBHOOK_SECRET=a\nMINIFLUX_PASSWORD=a\nMINIFLUX_USERNAME=admin\n"
		);
		expect(missingKeys(env, "external")).toEqual(["MINIFLUX_BASE_URL"]);
		expect(missingKeys(env, "bundled")).toEqual([]);
	});
});
