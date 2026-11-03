<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/lumia-logo-dark.avif" />
    <img src="docs/brand/lumia-logo-light.avif" alt="Lumia" width="340" />
  </picture>
</p>

<h3 align="center">Clarify your feeds. Learn your tastes.</h3>

<p align="center">
  A self-hosted RSS reader that keeps only the article, summarises it, reads it aloud<br />
  and learns what you like, without sending your reading anywhere.
</p>

<p align="center">
  <a href="https://techmefr.github.io/lumia/app/"><strong>Try the live demo</strong></a> ·
  <a href="https://techmefr.github.io/lumia/">Landing page</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="README.fr.md">Version française</a>
</p>

<p align="center">
  <a href="https://github.com/techmefr/lumia/actions/workflows/ci.yml"><img src="https://github.com/techmefr/lumia/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-6d63ee" alt="License AGPL-3.0" /></a>
  <img src="https://img.shields.io/badge/self--hosted-docker%20compose-4f46e5" alt="Self-hosted with docker compose" />
  <img src="https://img.shields.io/badge/WCAG-2.2%20AA-8b85f5" alt="WCAG 2.2 AA" />
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="docs/screenshots/articles-light.avif" />
    <img src="docs/screenshots/articles-dark.avif" alt="The Lumia article list, with folders, feeds and article cards" width="100%" />
  </picture>
</p>

## Why Lumia

- 🧹 **Just the article.** Every page is re-extracted: no banners, no menus, no "you may also like".
- ✨ **It learns your tastes.** Swipe through The Spark, and keywords, sources and authors you like
  rise to the top.
- 🎧 **Listen instead of reading.** Text-to-speech per article or across a whole playlist, sized to
  the time you have.
- 📍 **Pick up where you left off.** The reading position follows you from the laptop to the phone.
- 🔒 **Your reading stays home.** Summaries and keywords are computed locally; an AI key is optional.
- 📥 **Bring your feeds.** Feedly OPML import, Mastodon, Bluesky, Reddit, Google News, or save any
  page by URL.

## Screenshots

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/reader-dark.avif" alt="Reading view with keywords, export, translation and listen actions" /><br /><sub><b>Reader</b>: clean text, keywords, translate, listen, export to EPUB or PDF.</sub></td>
    <td width="50%"><img src="docs/screenshots/etincelle-dark.avif" alt="The Spark, a swipeable card to like, skip, favourite or keep for later" /><br /><sub><b>The Spark</b>: swipe to teach Lumia what you like.</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/screenshots/playlists-dark.avif" alt="Playlists with generated queues of 12, 25 or 45 minutes" /><br /><sub><b>Playlists</b>: a queue filled for the 12, 25 or 45 minutes you have.</sub></td>
    <td width="50%" align="center"><img src="docs/screenshots/mobile-dark.avif" alt="Lumia on a phone, with the bottom navigation bar" width="300" /><br /><sub><b>Mobile</b>: installable PWA with bottom navigation.</sub></td>
  </tr>
</table>

The [live demo](https://techmefr.github.io/lumia/app/) is the real front end running on made-up
articles: no account, no backend, nothing leaves the browser, and the banner's reset button starts it
over.

## Quick start

```bash
git clone https://github.com/techmefr/lumia.git
cd lumia
cp .env.example .env    # then fill in the secrets
docker compose up -d
```

Open `http://localhost:8080`: the app walks you through creating the admin account, then you import
an OPML file or add your first feeds. The details are under [Self-hosting](#self-hosting).

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
- **Exports** — an article or a playlist as JSON or EPUB, and as PDF through the browser's print dialog.
- **Paging** on every list, 24 articles at a time.

### Getting articles in

- **OPML import** (a Feedly export works as-is): one folder per category, each feed registered with
  Miniflux.
- **Add a feed by URL**, with the real feed title resolved from the source.
- **Social sources, through their public RSS**: paste a Mastodon profile or hashtag, a Bluesky
  profile, a Reddit subreddit or user, or a Google News search (or a short form such as `r/python`,
  `@user@mastodon.social`, `#tag@mastodon.social`, `@alice.bsky.social`, `news:climate`). No API key
  and no account are needed. Reddit is fetched with an honest User-Agent and Miniflux backs off on
  429/Retry-After; its public RSS is meant for non-commercial personal use, so keep it to your own
  reading.
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
- Navigation shortcuts: `g` then `a` articles, `e` the Spark, `f` feeds, `l` read later,
  `p` playlists, `v` favourites, `s` settings — the landing screen takes the focus. `?` opens the
  full list, and every single-key shortcut can be switched off in the settings (WCAG 2.1.4).
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

The app answers on `http://localhost:8080` and the API on `http://localhost:8000`. The API and Miniflux (8090)
are published on the loopback interface only; set `LUMIA_API_BIND=0.0.0.0` in `.env` to reach the API from
another machine. The worker, PostgreSQL and Redis stay on the internal network. The web container
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

The [`create-lumia`](packages/create-lumia/README.md) CLI automates the setup from a checkout:
`init` writes `.env` with generated secrets, `doctor` checks docker, ports and `.env`, `up` starts the
stack with the right compose files. It is not published to npm yet.

Already running your own Miniflux? Skip the bundled one with the second compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.external-miniflux.yml up -d
```

Set `MINIFLUX_BASE_URL`, `MINIFLUX_USERNAME` and `MINIFLUX_PASSWORD` in `.env` to your instance, and in
its Integrations settings point the webhook at `http://lumia-backend-api:8000/webhooks/miniflux` with
the same `MINIFLUX_WEBHOOK_SECRET` (use the address Miniflux can reach the API on if it does not share
a Docker network with Lumia). Feeds already in your Miniflux are listed in Lumia, where you tick the
ones to attach: nothing is copied on the Miniflux side. See
[issue #1](https://github.com/techmefr/lumia/issues/1) for the discussion.

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
| `apps/web`       | 1011  | 93%      | 92%   |

`packages/ui` covers every component and effect in the design system now, floor raised accordingly.
Every route page under `apps/web/src/routes/` now carries a suite of its own — the reader, the
subscriptions screen, the swipe piles, the playlists and the settings — which is what took that suite
from the 50s to the 90s. The `apps/web`
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
- **Translation.** A per-account DeepL key first, then the account's own LLM, then the instance
  `DEEPL_API_KEY` — whichever the account has actually configured. `DEEPL_API_KEY` is optional: an
  install with an LLM key and no DeepL key translates through the model, and one with neither keeps
  articles in their own language rather than failing on each of them. Articles are translated into
  the account's reading language when they arrive, and the article page carries a button to
  translate the one on screen into the interface language and to put the original back.

Keys are encrypted at rest (Fernet, `SECRET_ENCRYPTION_KEY`) and the API never returns them: it only
exposes `ai_api_key_set` / `translation_api_key_set`.

## License

[AGPL-3.0](LICENSE).
