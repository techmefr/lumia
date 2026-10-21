import { runMain } from "citty";
import { createNodeEnvironment } from "./adapters/node-environment.js";
import { createCli } from "./cli.js";

await runMain(createCli(createNodeEnvironment()));
