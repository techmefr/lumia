import { detectMode, meetsMinimumCompose, parseComposeVersion, portsFor } from "../compose.js";
import { missingKeys, parseEnv } from "../env-file.js";
import type { Environment, MinifluxMode } from "../types.js";

export type CheckStatus = "ok" | "warn" | "fail";

export interface Check {
	name: string;
	status: CheckStatus;
	detail: string;
}

export interface DoctorOptions {
	dir: string;
	miniflux?: MinifluxMode;
}

const checkDocker = async (env: Environment): Promise<Check> => {
	const result = await env.shell.capture("docker", ["--version"]);
	return result.code === 0
		? { name: "docker", status: "ok", detail: result.stdout.trim() }
		: { name: "docker", status: "fail", detail: "docker is not installed or not on the PATH" };
};

const checkCompose = async (env: Environment): Promise<Check> => {
	const result = await env.shell.capture("docker", ["compose", "version"]);
	const version = result.code === 0 ? parseComposeVersion(result.stdout) : undefined;
	if (version === undefined) {
		return { name: "compose", status: "fail", detail: "docker compose v2 is not available" };
	}
	return meetsMinimumCompose(version)
		? { name: "compose", status: "ok", detail: version.join(".") }
		: {
				name: "compose",
				status: "fail",
				detail: `${version.join(".")} found, 2.24 or newer is required`
			};
};

const checkPorts = (mode: MinifluxMode, env: Environment): Promise<Check[]> =>
	Promise.all(
		portsFor(mode).map(async ({ port, service }): Promise<Check> =>
			(await env.network.isPortFree(port))
				? { name: `port ${port}`, status: "ok", detail: `free for ${service}` }
				: {
						name: `port ${port}`,
						status: "warn",
						detail: `in use, ${service} cannot bind it unless Lumia is already running`
					}
		)
	);

const checkEnvFile = (values: Map<string, string> | undefined, mode: MinifluxMode): Check => {
	if (values === undefined) {
		return { name: ".env", status: "fail", detail: "missing, run create-lumia init" };
	}
	const missing = missingKeys(values, mode);
	return missing.length === 0
		? { name: ".env", status: "ok", detail: "required keys are set" }
		: {
				name: ".env",
				status: "fail",
				detail: `unset or still a placeholder: ${missing.join(", ")}`
			};
};

const checkMiniflux = async (url: string | undefined, env: Environment): Promise<Check> => {
	if (url === undefined || url === "") {
		return { name: "miniflux", status: "fail", detail: "MINIFLUX_BASE_URL is not set" };
	}
	return (await env.network.isReachable(url))
		? { name: "miniflux", status: "ok", detail: `${url} answers` }
		: { name: "miniflux", status: "fail", detail: `${url} is unreachable from this machine` };
};

const report = (checks: Check[], env: Environment): void => {
	for (const check of checks) {
		const line = `${check.name}: ${check.detail}`;
		if (check.status === "ok") env.logger.success(line);
		else if (check.status === "warn") env.logger.warn(line);
		else env.logger.error(line);
	}
};

export const runDoctor = async (options: DoctorOptions, env: Environment): Promise<Check[]> => {
	const envPath = env.join(options.dir, ".env");
	const values = (await env.fs.exists(envPath)) ? parseEnv(await env.fs.read(envPath)) : undefined;
	const mode = options.miniflux ?? (values === undefined ? "bundled" : detectMode(values));

	const checks = [
		await checkDocker(env),
		await checkCompose(env),
		...(await checkPorts(mode, env)),
		checkEnvFile(values, mode)
	];
	if (mode === "external") checks.push(await checkMiniflux(values?.get("MINIFLUX_BASE_URL"), env));

	report(checks, env);
	return checks;
};

export const isHealthy = (checks: Check[]): boolean =>
	checks.every((check) => check.status !== "fail");
