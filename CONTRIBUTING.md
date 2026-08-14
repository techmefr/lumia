# Contributing to Lumia

Thanks for considering contributing. Lumia is AGPL-3.0 and community-driven — any deployed fork must publish its source, including over a network.

## Ground rules

- Code and commits are in English (conventional commits: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`…).
- TypeScript is strict, no `any`.
- Names carry the *what*; a comment is for the *why* — a constraint, a trade-off, a rule that isn't obvious from the code. No comments that restate the line below them.
- Respect the OSDD split: `technical/` for cross-cutting concerns, `domain/` for business logic, per bounded context (`feed`, `article`, `user`, `recommendation`, `audio`).
- UI changes follow the "Digital Paper" design system (see `packages/ui/technical/tokens.css`) and must meet RGAA 4.1 AA.

## Workflow

1. Open an issue first for anything beyond a small fix (use the templates under `.github/ISSUE_TEMPLATE/`).
2. Fork or branch, one focused change per PR.
3. Add tests for new behavior.
4. Open a PR against `main` describing what changed and why.

## Project structure

See [ARCHITECTURE.md](ARCHITECTURE.md) before adding a new module — figure out which app/package and which bounded context it belongs to before writing code.

## Local setup

```bash
docker compose up -d
```

This starts PostgreSQL, Miniflux, the API, and the worker. Frontend apps (`apps/web`, `apps/mobile`, `apps/extension`) run separately during development — see each app's own README once available.

## Running the checks

The backend gate runs in its own image (the `dev` stage of `docker/lumia-backend/Dockerfile`, which adds ruff, mypy and pytest on top of the runtime dependencies), against a `lumia_test` database:

```bash
docker compose run --rm --build lumia-backend-tests sh -c 'ruff check . && mypy . && pytest -q'
```

`--build` matters: the image copies the source in rather than mounting it, so without it the checks run against the previous build.

The frontend gate:

```bash
pnpm --filter web check
```

