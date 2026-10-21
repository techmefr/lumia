import { composeFileVariable } from "../compose.js";
import { applyValues, buildEnvValues } from "../env-file.js";
import type { Environment, MinifluxMode } from "../types.js";

export interface InitOptions {
	dir: string;
	miniflux?: MinifluxMode;
	minifluxUrl?: string;
	frontendUrl?: string;
	yes: boolean;
	force: boolean;
}

export class InitError extends Error {}

const resolveMode = async (options: InitOptions, env: Environment): Promise<MinifluxMode> => {
	if (options.miniflux !== undefined) return options.miniflux;
	if (options.minifluxUrl !== undefined) return "external";
	if (options.yes) return "bundled";
	return env.prompter.select<MinifluxMode>("Which Miniflux should Lumia use?", [
		{ label: "Bundled (started with Lumia)", value: "bundled" },
		{ label: "External (my own instance)", value: "external" }
	]);
};

const resolveMinifluxUrl = async (options: InitOptions, env: Environment): Promise<string> => {
	const url =
		options.minifluxUrl ??
		(options.yes ? "" : await env.prompter.text("Address of your Miniflux", "https://"));
	if (!/^https?:\/\/[^\s/]+/.test(url)) {
		throw new InitError(
			"An external Miniflux needs --miniflux-url, for example https://rss.example.org"
		);
	}
	return url.replace(/\/+$/, "");
};

const mayWrite = async (envPath: string, options: InitOptions, env: Environment): Promise<boolean> => {
	if (!(await env.fs.exists(envPath))) return true;
	if (options.force) return true;
	if (options.yes) throw new InitError(".env already exists; pass --force to replace it");
	return env.prompter.confirm(".env already exists. Replace it with freshly generated secrets?");
};

export const runInit = async (options: InitOptions, env: Environment): Promise<boolean> => {
	const examplePath = env.join(options.dir, ".env.example");
	if (!(await env.fs.exists(examplePath))) {
		throw new InitError(`No .env.example in ${options.dir}: run this from a Lumia checkout`);
	}
	const envPath = env.join(options.dir, ".env");
	if (!(await mayWrite(envPath, options, env))) {
		env.logger.info("Kept the existing .env");
		return false;
	}

	const mode = await resolveMode(options, env);
	const minifluxBaseUrl = mode === "external" ? await resolveMinifluxUrl(options, env) : undefined;
	const values = buildEnvValues({
		mode,
		minifluxBaseUrl,
		frontendUrl: options.frontendUrl,
		composeFile: composeFileVariable(mode),
		randomBytes: env.randomBytes
	});
	await env.fs.write(envPath, applyValues(await env.fs.read(examplePath), values));
	env.logger.success(`Wrote ${envPath} with generated secrets (${mode} Miniflux)`);
	if (mode === "external") {
		env.logger.info(
			"Set MINIFLUX_USERNAME and MINIFLUX_PASSWORD in .env to an account on your Miniflux"
		);
	}
	env.logger.info("Next: create-lumia doctor, then create-lumia up");
	return true;
};
