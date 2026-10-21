import type { Environment } from "../types.js";

export interface FakeEnvironment extends Environment {
	files: Map<string, string>;
	logs: string[];
	streamed: { command: string; args: string[]; cwd: string }[];
	answers: { confirm: boolean[]; text: string[]; select: string[] };
	capturedResults: Map<string, { code: number; stdout: string }>;
	busyPorts: Set<number>;
	unreachable: Set<string>;
	streamCode: number;
}

export const createFakeEnvironment = (initial: Record<string, string> = {}): FakeEnvironment => {
	const files = new Map(Object.entries(initial));
	const logs: string[] = [];
	const environment: FakeEnvironment = {
		files,
		logs,
		streamed: [],
		answers: { confirm: [], text: [], select: [] },
		capturedResults: new Map(),
		busyPorts: new Set(),
		unreachable: new Set(),
		streamCode: 0,
		fs: {
			exists: async (path) => files.has(path),
			read: async (path) => {
				const content = files.get(path);
				if (content === undefined) throw new Error(`missing ${path}`);
				return content;
			},
			write: async (path, content) => {
				files.set(path, content);
			}
		},
		shell: {
			capture: async (command, args) =>
				environment.capturedResults.get([command, ...args].join(" ")) ?? { code: 127, stdout: "" },
			stream: async (command, args, cwd) => {
				environment.streamed.push({ command, args, cwd });
				return environment.streamCode;
			}
		},
		network: {
			isPortFree: async (port) => !environment.busyPorts.has(port),
			isReachable: async (url) => !environment.unreachable.has(url)
		},
		prompter: {
			confirm: async () => environment.answers.confirm.shift() ?? false,
			text: async (_message, initialValue) => environment.answers.text.shift() ?? initialValue,
			select: async (_message, options) =>
				(environment.answers.select.shift() ?? options[0]?.value ?? "") as never
		},
		logger: {
			info: (message) => logs.push(`info ${message}`),
			success: (message) => logs.push(`success ${message}`),
			warn: (message) => logs.push(`warn ${message}`),
			error: (message) => logs.push(`error ${message}`)
		},
		randomBytes: (size) => Buffer.alloc(size, 7),
		join: (...parts) => parts.join("/")
	};
	return environment;
};
