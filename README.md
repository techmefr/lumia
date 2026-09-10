# Lumia

> Clarify your feeds. Learn your tastes.

Lumia is a self-hosted RSS reader that pulls your feeds, strips the articles down to the actual
article, extracts keywords and a summary, and learns what interests you as you read. Everything runs
on your own machine.

**[Landing page](https://techmefr.github.io/lumia/)** ·
**[Live demo](https://techmefr.github.io/lumia/app/)** ·
Version française : [README.fr.md](README.fr.md)

The demo is the real front end with the http client swapped for an in-memory one seeded with made-up
articles. Nothing leaves the browser, there is no account and no backend behind it; the reset button
in the banner clears the seeded state. It exists to judge the interface, the reading view and the
text-to-speech on a real device before installing anything.

## What it does

### Reading

- **Full, readable articles.** Every page is re-fetched and re-extracted with
  [trafilatura](https://trafilatura.readthedocs.io) to drop navigation, banners and related-article
  lists. Feed-crawler extraction alone routinely leaks site chrome into the body.
- **Estimated reading time** on every card, from the article's word count.
- **Reading position saved server-side.** Reopen an article on another device and it resumes where
  you stopped. The stored position never rewinds, so a quick revisit that lands at the top can't
  erase your progress.
- **Progress bar** at the top of the article, and an article past 90 % read marks itself read.
- **Text-to-speech**, per article or across a whole playlist.

### Organising

- **Read/unread** with unread counts per feed and per folder, an unread-only filter, and
  "mark everything read" scoped to a feed, a folder, an explicit list of articles, or the whole
  library — the API requires exactly one scope, so a forgotten filter can't mark it all read by
  accident, and marking the whole library asks for confirmation past ten unread articles.
- **Folders** you can rename and delete; deleting one unfiles its feeds instead of taking them with
  it. Feeds can be retitled and moved between folders.
- **Search** across title, summary and content, combinable with the folder/feed/author/keyword
  filters.
- **Playlists** — ordered queues of articles with a total duration, reorderable, readable aloud
  end to end.
- **Paging** on every list, 24 articles at a time.

### Getting articles in

- **OPML import** (a Feedly export works as-is): one folder per category, each feed registered with
  Miniflux.
- **Add a feed by URL**, with the real feed title resolved from the source.
- **Save any page by URL**, Pocket-style: the page is extracted and filed on a per-user
  "Enregistrés" feed. Re-saving the same URL returns the existing article rather than duplicating it.
- **Translation** of foreign-language articles (DeepL).

### Learning

- **L'Étincelle** — a relevance score learned from your votes and applied to keywords, sources,
  authors and categories. Swipe right to like, left to skip.
- Feedback is split into independent axes: sentiment (like/dislike), saved, favorite, read.

### Interface

- Keyboard shortcuts: `j`/`k` to move, `o` to open, `m` read/unread, `s` save, `u` unread-only,
  `f` flip through, `/` search, always listed at the bottom of the article list.
- Skeleton loaders, actionable empty states, and toasts with undo on destructive actions.
- Light/dark, adjustable text size, page transitions, `prefers-reduced-motion` honoured throughout.
- WCAG 2.2 AA: skip link, `aria-current` on navigation, live regions on async state, native radio
  groups rather than ARIA imitations, and a palette checked by measured contrast rather than by eye.

## Architecture

Monorepo, OSDD (`technical/` / `domain/` split in every app and service; `technical/` never imports
`domain/`).

```
lumia/
├── packages/
│   ├── ui/       Shared Svelte 5 components (primitives, effects, article card)
│   └── core/     Shared logic (feed, article, user, recommendation, playlist)
├── apps/
│   ├── web/          SvelteKit SPA
│   ├── mobile/       Svelte + Capacitor (iOS/Android) — planned
│   ├── extension/    WebExtension (Chrome/Firefox) — planned
│   └── auto/         Android Auto (Kotlin, audio only) — planned
├── backend/
│   ├── api/       FastAPI
│   └── worker/    Python enrichment pipeline (TF-IDF, FR/EN stemming, extractive summary)
└── landing/       Static landing page, deployed to GitHub Pages
```

Stack: FastAPI, PostgreSQL, Redis, arq, Miniflux for ingestion, SvelteKit + Svelte 5 + Tailwind 4 on
the front. Keyword extraction and summarization are local — no external AI call is required to read.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown and [CONTRIBUTING.md](CONTRIBUTING.md)
to contribute.

## Self-hosting

```bash
git clone https://github.com/techmefr/lumia.git
cd lumia
cp .env.example .env    # then fill in the secrets
docker compose up -d
```

The API exposes `GET /health` (the process answers, no I/O) and `GET /ready` (PostgreSQL and Redis
answer, `503` and which one is down otherwise). Every service in the compose file has a healthcheck
built on them, and the API, the worker and the web container wait for what they depend on to be
healthy rather than merely started — point your own supervision at `/health`.

The app answers on `http://localhost:8080` and the API on `http://localhost:8000`. Only those two are
exposed; Miniflux, the worker, PostgreSQL and Redis stay on the internal network. The web container
serves the static build behind nginx and proxies `/api` to the API, so the app works from any address
with no configuration and no CORS. On first launch the app walks you through admin onboarding: admin account, instance
limits (max accounts, per-user disk quota), then you're ready to import an OPML file or add feeds.

`ADMIN_EMAIL`, `ADMIN_USERNAME` and `ADMIN_PASSWORD` skip that onboarding screen: the admin account is
created at the first start that finds the schema in place (so after the migrations below, on the next
restart), and a later restart neither creates a second one nor rewrites its password. `MAX_ACCOUNTS` and `ACCOUNT_QUOTA_MB` only seed the instance quotas — from then
on the admin owns both numbers, in the Administration section of the settings, which also lists every
account with what it stores and carries the pending access requests. That section sits behind
`require_admin`: a member neither sees it nor can call its routes.

`FRONTEND_URL` (defaults to `http://localhost:8080`, the docker-compose default) is only used to
build the clickable link in the "sign in without a password" email; set it to the app's real address
if it's reached from a domain or a LAN address instead.

`MINIFLUX_WEBHOOK_SECRET` is required: Miniflux signs every webhook call with it
(`X-Miniflux-Signature`), and the API rejects anything that doesn't match rather than trusting
whatever reaches `/webhooks/miniflux`. Set it once in `.env` before the first `docker compose up`,
the same value on both sides — the compose file already wires it to both.

Already running your own Miniflux instead of the bundled one? Point `MINIFLUX_BASE_URL` at it and
set its webhook the same way; see [issue #1](https://github.com/techmefr/lumia/issues/1) for the
walkthrough and the current limits (feeds already in Miniflux don't attach to Lumia on their own
yet — [issue #11](https://github.com/techmefr/lumia/issues/11) tracks that).

To reach it from a phone or tablet on the same network, use the machine's LAN address rather than
`localhost`. The [landing page](https://techmefr.github.io/lumia/) can store that address per device
and give you a direct button.

### Database migrations

```bash
docker compose exec lumia-backend-api uv run alembic upgrade head
```

## Development

```bash
pnpm install
pnpm --filter web dev      # front on :5173
pnpm --filter web check    # svelte-check
pnpm --filter web build
```

Backend, from `backend/`:

```bash
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

The backend suite needs PostgreSQL and Redis reachable. It defaults to
`postgresql+asyncpg://lumia:lumia@localhost:55432/lumia_test` and `redis://localhost:6379/1`, which
two throwaway containers provide:

```bash
docker run -d --name lumia-test-db -p 55432:5432 -e POSTGRES_USER=lumia -e POSTGRES_PASSWORD=lumia -e POSTGRES_DB=lumia_test postgres:16-alpine
docker run -d --name lumia-test-redis -p 6379:6379 redis:7-alpine
```

### Tests and coverage

Four suites, each with its own coverage floor enforced on every push:

```bash
uv run pytest                             # backend, from backend/
pnpm --filter @lumia/core test:coverage   # shared api contracts and http client
pnpm --filter @lumia/ui test:coverage     # design system components
pnpm --filter web test:coverage           # app stores, i18n, demo client
```

| Suite            | Tests | Coverage | Floor |
| ---------------- | ----- | -------- | ----- |
| `backend`        | 318   | 86%      | 80%   |
| `packages/core`  | 108   | 100%     | 80%   |
| `packages/ui`    | 319   | 99%      | 98%   |
| `apps/web`       | 578   | 49%      | 50%   |

`packages/ui` covers every component and effect in the design system now, floor raised accordingly.
`apps/web` now covers the feed sidebar, the flip reader and the swipe stack too; the remaining gap
is the route pages under `src/routes/` themselves — roughly 3000 lines still with no dedicated test.
The `apps/web`
floor is a ratchet, not a target: 80% is the target everywhere. Raise a floor when you add tests;
never lower one to turn a red run green. See [CONTRIBUTING.md](CONTRIBUTING.md) for how the tests are
written.

### Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request:

- **frontend** — `svelte-check`, then the three vitest suites with their coverage floors
- **backend** — ruff, ruff format, mypy, pytest with its coverage floor, against a real PostgreSQL
- **migrations** — `alembic upgrade head` on an empty database, then down to `base` and back up, so a
  release can be rolled back and re-applied
- **docker** — the backend image builds

## AI and translation keys

Everything is per account, under **Réglages → IA et traduction**; there is no instance-wide key.

- **Summarization.** With no key, the summary is extractive and computed locally. With a key it goes
  through a model: Mistral, OpenAI, Anthropic, Gemma (Google's own OpenAI-compatible endpoint), or a
  Custom endpoint — vLLM, Ollama, llama.cpp, Voxtral, a local Gemma, anything that speaks the
  `/chat/completions` shape. Custom needs the URL and the model name, which can't be guessed. An
  unreachable provider or a rejected key doesn't cost the article its summary: it falls back to the
  extractive one.
- **Translation.** A per-account DeepL key, falling back to the instance `DEEPL_API_KEY`. The target
  language is the account's reading language.

Keys are encrypted at rest (Fernet, `SECRET_ENCRYPTION_KEY`) and the API never returns them: it only
exposes `ai_api_key_set` / `translation_api_key_set`.

## License

[AGPL-3.0](LICENSE).
