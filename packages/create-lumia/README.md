# create-lumia

Sets up, checks and starts a self-hosted [Lumia](../../README.md) instance from a checkout of the
repository. Built with [citty](https://github.com/unjs/citty) and [consola](https://github.com/unjs/consola).

Not published yet: build it from the repository.

```bash
pnpm --filter create-lumia build
node packages/create-lumia/dist/index.js --help
```

Every command takes the checkout directory as an optional argument (default: the current directory).

## `init`

Copies `.env.example` to `.env` and fills the secrets with values from `node:crypto`: database
password, JWT secret, Fernet encryption key, Miniflux webhook secret and, for the bundled Miniflux, its
admin password. Secrets are never printed. The file is written with mode `0600`.

```bash
create-lumia init                                   # interactive
create-lumia init --yes                             # bundled Miniflux, no prompt
create-lumia init --yes --miniflux-url https://rss.example.org
create-lumia init --yes --force                     # replace an existing .env
```

| Flag | Meaning |
| --- | --- |
| `--miniflux bundled\|external` | Which Miniflux Lumia uses. `--miniflux-url` implies `external`. |
| `--miniflux-url` | Address of your Miniflux. Writes `MINIFLUX_BASE_URL` and `COMPOSE_FILE` so `docker-compose.external-miniflux.yml` is applied. |
| `--frontend-url` | Public address of the web app (`FRONTEND_URL`). |
| `--yes` | Never prompt. Fails if a value cannot be defaulted or if `.env` exists without `--force`. |
| `--force` | Replace an existing `.env`. Without it, interactive mode asks first. |

For an external Miniflux, fill `MINIFLUX_USERNAME` and `MINIFLUX_PASSWORD` in `.env` yourself: they belong
to an account that already exists on that instance.

## `doctor`

Checks docker, the compose version (2.24 or newer, for the `!override` tag), that ports 8080, 8000 and,
with the bundled Miniflux, 8090 are free, that the required `.env` keys are set and not left at
`change-me`, and, for an external Miniflux, that its address answers. Exits with 1 when a check fails;
a busy port is a warning because Lumia itself may be running.

## `up`

Runs `docker compose up -d` with the right `-f` files, streaming docker's output. The mode comes from
`COMPOSE_FILE` in `.env`, or from `--miniflux`. `--foreground` stays attached.

## Development

```bash
pnpm --filter create-lumia test
pnpm --filter create-lumia check
pnpm --filter create-lumia build
```

Decisions live in pure modules (`env-file.ts`, `compose.ts`) and in command functions that receive an
`Environment` (filesystem, shell, network, prompts, logger). `src/adapters/` holds the only real
implementation; tests use `src/test-support/fake-environment.ts`.
