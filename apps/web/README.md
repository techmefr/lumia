# Lumia web app

The SvelteKit single-page app, built with `@sveltejs/adapter-static` and served by nginx in the
`lumia-web` image. Run every command from the repository root after `pnpm install`.

## Develop

```bash
pnpm --filter web dev          # on http://localhost:5173, talking to the API on :8000
VITE_DEMO=true pnpm --filter web dev   # the seeded demo: no backend needed
```

## Check and test

```bash
pnpm --filter web check           # svelte-check
pnpm --filter web test:coverage   # vitest, with the coverage floors of vite.config.ts
pnpm --filter web test:e2e        # Playwright journeys and axe checks against the demo build
```

## Build

```bash
pnpm --filter web build           # static site in apps/web/build
pnpm --filter web build:mobile    # the bundle the Capacitor app ships, see apps/mobile
```

`BASE_PATH` serves the build under a sub-path, as the GitHub Pages demo does with `/lumia/app`.
