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

## Writing tests

Every new behaviour comes with a test. Four suites, one per package, each next to the code it covers
(`foo.ts` → `foo.test.ts`).

**Select on `data-test-*`, never on a class.** The classes in this codebase exist for visual reasons
and change on a design pass; a suite hanging off them goes red for reasons that have nothing to do
with behaviour. Add the hook to the component when you test it — see
`packages/ui/domain/article-card.svelte` and its test for the pattern.

**Assert on what the code does, not on a double.** A test whose subject is a mock confirms the mock
works. Mock only at the outer boundary — the network, the clock, the browser api — and assert on the
value returned, the state changed, or what the request carried. `packages/core/test-support/recording-http-client.ts`
exists for exactly that: the api modules turn arguments into one request, and that request is their
observable output.

**Wait on a condition, never on a duration.** `setTimeout` then assert is a bet on machine speed
that passes locally and fails in CI under load. If a test needs longer, the timeout is raised in the
config, once, for everyone — never by shortening the scenario to fit.

**Never weaken a test to make it pass.** Loosening an assertion, deleting a case or lowering a
coverage floor turns a real signal into a green tick. If a case cannot be expressed in the
environment (jsdom implements neither `contentEditable` nor `CSS.highlights`, for instance), say so
in the test rather than watering it down — or make the production code testable when doing so is a
genuine improvement.

Coverage floors are ratchets. `backend` and `packages/core` sit at 80%; `packages/ui` and `apps/web`
are floored just under what they cover today and go up with each batch of tests. Raise a floor when
you add tests; never lower one.

## Running the checks

Everything CI runs, runnable locally. Frontend, from the repo root:

```bash
pnpm --filter web check
pnpm --filter @lumia/core test:coverage
pnpm --filter @lumia/ui test:coverage
pnpm --filter web test:coverage
```

Backend, from `backend/`, against a throwaway PostgreSQL on `:55432` (see the README for the one
`docker run` that provides it):

```bash
uv sync --all-groups
uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest
```

Or in the project's own image, which copies the source in rather than mounting it:

```bash
docker compose run --rm --build lumia-backend-tests sh -c 'ruff check . && mypy . && pytest -q'
```

`--build` matters: without it the checks run against the previous build, and a green result says
nothing about what you just wrote.

A migration is not finished until it survives a round trip. Dropping a table does not drop the enum
type it used, so a downgrade that only drops tables makes the next upgrade fail:

```bash
uv run alembic upgrade head && uv run alembic downgrade base && uv run alembic upgrade head
```

