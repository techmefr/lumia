import { composeArgs, detectMode } from "../compose.js";
import { parseEnv } from "../env-file.js";
import type { Environment, MinifluxMode } from "../types.js";

export interface UpOptions {
	dir: string;
	miniflux?: MinifluxMode;
	foreground: boolean;
}

export class UpError extends Error {}

export const runUp = async (options: UpOptions, env: Environment): Promise<number> => {
	const envPath = env.join(options.dir, ".env");
	if (!(await env.fs.exists(envPath))) {
		throw new UpError(".env is missing, run create-lumia init first");
	}
	const mode = options.miniflux ?? detectMode(parseEnv(await env.fs.read(envPath)));
	const subcommand = options.foreground ? ["up"] : ["up", "-d"];
	env.logger.info(`Starting Lumia with the ${mode} Miniflux`);
	const code = await env.shell.stream("docker", composeArgs(mode, subcommand), options.dir);
	if (code === 0) env.logger.success("docker compose finished, the web app listens on port 8080");
	else env.logger.error(`docker compose exited with code ${code}`);
	return code;
};
