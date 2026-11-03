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
  <a href="#requirements">Requirements</a> ·
  <a href="#install">Install</a> ·
  <a href="https://techmefr.github.io/lumia/">Landing page</a> ·
  <a href="README.fr.md">Version française</a>
</p>

<p align="center">
  <a href="https://github.com/techmefr/lumia/actions/workflows/ci.yml"><img src="https://github.com/techmefr/lumia/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-6d63ee" alt="License AGPL-3.0" /></a>
  <img src="https://img.shields.io/badge/self--hosted-docker%20compose-4f46e5" alt="Self-hosted with docker compose" />
  <img src="https://img.shields.io/badge/arch-amd64%20%7C%20arm64-8b85f5" alt="Runs on amd64 and arm64" />
  <img src="https://img.shields.io/badge/WCAG-2.2%20AA-a49cf8" alt="WCAG 2.2 AA" />
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="docs/screenshots/articles-light.avif" />
    <img src="docs/screenshots/articles-dark.avif" alt="The Lumia article list, with folders, feeds and article cards" width="100%" />
  </picture>
</p>

## Why Lumia

- 🧹 **Just the article.** Every page is re-extracted: no banners, no menus, no "you may also like".
- ✨ **It learns your tastes.** Swipe through The Spark, and the keywords, sources and authors you
  like rise to the top.
- 🎧 **Listen instead of reading.** Text-to-speech per article or across a whole playlist, sized to
  the time you have, and podcasts in the same player.
- 📍 **Pick up where you left off.** The reading position follows you from the laptop to the phone.
- 🔒 **Your reading stays home.** Summaries and keywords are computed locally; an AI key is optional.
- 📥 **Bring everything in.** Feedly OPML, Mastodon, Bluesky, Reddit, YouTube, Google News,
  newsletters, or any page saved by URL.
- 📱 **On every screen.** Installable web app, browser extension, and your usual reader app through
  the Fever API.

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

## Try it in 10 seconds

The [live demo](https://techmefr.github.io/lumia/app/) is the real front end running on made-up
articles: no account, no backend, nothing leaves your browser. Open an article, swipe The Spark,
listen to a playlist; the banner's reset button starts it over.

## Requirements

Lumia runs as seven containers: the web app, the API, the worker, PostgreSQL, Redis, and Miniflux
with its own PostgreSQL.

| | Minimum | Comfortable |
| --- | --- | --- |
| **Machine** | Any x86_64 or ARM64 Linux host: a small VPS, a NAS, a Raspberry Pi 4 or 5 | A home server or a 2 vCPU VPS |
| **Memory** | 2 GB in total: Lumia itself uses about 0.6 GB at rest and 1.1 GB at peak | 4 GB, room for the OS and the build |
| **CPU** | 1 core | 2 cores, for the bursts when many new articles arrive at once |
| **Disk** | 5 GB: about 1.5 GB of images, the build cache, and the database | 20 GB or more; an article takes about 55 KB in the database |
| **Software** | Docker Engine with Compose v2.24 or later | |
| **Network** | Outbound internet access to fetch the feeds | A domain and HTTPS if you read from outside your home |

These numbers were measured on the full stack with 25 real feeds: about 600 MB of memory at rest, 1.1 GB while 272 new articles were enriched at once, and a database of 15 MB for those 272 articles. During such a burst the worker uses every core it can get; on a single core the same burst simply takes longer.

**Ports.** The app answers on `8080`. The API (`8000`) and Miniflux (`8090`) are published on the
loopback interface only; PostgreSQL, Redis and the worker are never published.

**Optional, never required:**

| To get | You need |
| --- | --- |
| Emails (passwordless sign-in, password reset, invitations, digest) | An SMTP account |
| AI summaries, chat and tag suggestions | An API key from Mistral, OpenAI, Anthropic or Google, or your own endpoint (Ollama, vLLM, llama.cpp…) |
| Translation | A DeepL key, or the AI key above |
| Natural voices | An OpenAI-compatible speech endpoint; the browser's own voices work without anything |

Without any of these, Lumia reads, extracts, summarises, ranks and reads aloud on its own.

## Install

```bash
git clone https://github.com/techmefr/lumia.git
cd lumia
cp .env.example .env
```

Fill in every `change-me` in `.env`. Two of them have a required format:

```bash
openssl rand -hex 32    # JWT_SECRET, POSTGRES_PASSWORD, MINIFLUX_PASSWORD, MINIFLUX_WEBHOOK_SECRET
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"    # SECRET_ENCRYPTION_KEY
```

Leave `DEEPL_API_KEY` empty if you don't have one, and the `SMTP_*` lines as they are if you don't
send emails. Then start the stack and create the database schema:

```bash
docker compose up -d --build
docker compose exec lumia-backend-api alembic upgrade head
```

The first build takes a few minutes. Open **http://localhost:8080**: the app walks you through
creating the admin account and the instance limits, then you import an OPML file or add your first
feeds. From a phone or a tablet on the same network, use the machine's address instead of
`localhost`.

The [`create-lumia`](packages/create-lumia/README.md) CLI does the `.env` part for you from a checkout:
`init` writes it with generated secrets, `doctor` checks Docker, the ports and `.env`, and `up` starts
the stack.

### Update

```bash
git pull
docker compose up -d --build
docker compose exec lumia-backend-api alembic upgrade head
```

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
- **Text-to-speech**, per article or across a whole playlist, and **podcast episodes** played in the
  same persistent player, streamed from the feed's host.
- **Highlights and notes** on passages, gathered on their own page.
- **Ask the article**: a chat about the article on screen, through your own AI provider.
- **Translation** of foreign-language articles, through DeepL or your AI provider, with a button to
  put the original back.

### Organising

- **Read/unread** with unread counts per feed and per folder, an unread-only filter, and
  "mark everything read" scoped to a feed, a folder, an explicit list of articles, or the whole
  library — the API requires exactly one scope, so a forgotten filter can't mark it all read by
  accident, and marking the whole library asks for confirmation past ten unread articles.
- **Folders** you can rename and delete; deleting one unfiles its feeds instead of taking them with
  it. Feeds can be retitled and moved between folders.
- **Search** across title, summary and content, combinable with the folder/feed/author/keyword
  filters, and **saved searches** that raise an **alert** when a new article matches.
- **Tags** of your own on any article, with AI suggestions when a key is set.
- **Playlists** — ordered queues of articles with a total duration, reorderable, readable aloud
  end to end, or generated for the 12, 25 or 45 minutes you have.
- **Exports** — an article or a playlist as JSON or EPUB, and as PDF through the browser's print dialog.
- **Public share links** for a single article.
- **Statistics** on what you read, and an opt-in **email digest** of your best-ranked unread articles.

### Getting articles in

- **OPML import** (a Feedly export works as-is): one folder per category, each feed registered with
  Miniflux.
- **Add a feed by URL**, with the real feed title resolved from the source.
- **Social sources, through their public RSS**: paste a Mastodon profile or hashtag, a Bluesky
  profile, a Reddit subreddit or user, a YouTube channel, or a Google News search (or a short form
  such as `r/python`, `@user@mastodon.social`, `#tag@mastodon.social`, `@alice.bsky.social`,
  `news:climate`). No API key and no account are needed. Reddit is fetched with an honest User-Agent
  and Miniflux backs off on 429/Retry-After; its public RSS is meant for non-commercial personal use,
  so keep it to your own reading.
- **Newsletters** without a mail server: each reader gets a secret inbound address, and any forwarder
  that can POST JSON delivers the issues as articles.
- **Save any page by URL**, Pocket-style, from the app or the browser extension: the page is extracted
  and filed on a per-user "Enregistrés" feed. Re-saving the same URL returns the existing article
  rather than duplicating it.

### Learning

- **L'Étincelle** (The Spark) — a relevance score learned from your votes and applied to keywords,
  sources, authors and categories. Swipe right to like, left to skip, up to favourite, down to keep
  for later.
- Feedback is split into independent axes: sentiment (like/dislike), saved, favorite, read.

### Other clients and integrations

- **Browser extension** for Chrome and Firefox: save the current page or a link, and read in the
  side panel.
- **Fever API**, so Reeder, NetNewsWire, Fiery Feeds or ReadKit sync with Lumia.
- **Outbound webhooks**, signed, on saved, favourited and added-to-playlist articles.
- **Mobile app** (Capacitor, iOS and Android) and **Android Auto** (audio only) in
  [`apps/mobile`](apps/mobile/README.md) and [`apps/auto`](apps/auto/README.md).

### Accounts and security

- Admin onboarding on first launch, then accounts by **invitation** or access request, within the
  instance's account and disk quotas.
- **Passwordless sign-in** by email, **two-factor authentication** (TOTP, with recovery codes), and
  revocation of every session from the settings.
- AI and translation keys are per account, encrypted at rest, and never returned by the API.

### Interface

- Keyboard shortcuts: `j`/`k` to move, `o` to open, `m` read/unread, `s` save, `u` unread-only,
  `f` flip through, `/` search, `x` select, `shift+j`/`shift+k` extend the selection, `shift+a`
  select all, always listed at the bottom of the article list.
- Navigation shortcuts: `g` then `a` articles, `e` the Spark, `f` feeds, `l` read later,
  `p` playlists, `v` favourites, `t` statistics, `s` settings — the landing screen takes the focus.
  `?` opens the full list, and every single-key shortcut can be switched off in the settings
  (WCAG 2.1.4).
- Seven themes (light, dark, Dracula, Alucard, Nord, Solarized light and dark), adjustable text size
  and reading fonts, page transitions, `prefers-reduced-motion` honoured throughout.
- Skeleton loaders, actionable empty states, and toasts with undo on destructive actions.
- WCAG 2.2 AA: skip link, `aria-current` on navigation, live regions on async state, native radio
  groups rather than ARIA imitations, and a palette checked by measured contrast rather than by eye.
  See [docs/accessibility.md](docs/accessibility.md).

## Self-hosting in detail

The API exposes `GET /health` (the process answers, no I/O) and `GET /ready` (PostgreSQL and Redis
answer, `503` and which one is down otherwise). Every service in the compose file has a healthcheck
built on them, and the API, the worker and the web container wait for what they depend on to be
healthy rather than merely started — point your own supervision at `/health`.

The web container serves the static build behind nginx and proxies `/api` to the API, so the app
works from any address with no configuration and no CORS. Set `LUMIA_API_BIND=0.0.0.0` in `.env` to
reach the API itself from another machine, with `TRUST_PROXY_HEADERS=false`.

`ADMIN_EMAIL`, `ADMIN_USERNAME` and `ADMIN_PASSWORD` skip the onboarding screen: the admin account is
created at the first start that finds the schema in place (so after the migrations, on the next
restart), and a later restart neither creates a second one nor rewrites its password.
`MAX_ACCOUNTS` and `ACCOUNT_QUOTA_MB` only seed the instance quotas — from then on the admin owns both
numbers, in the Administration section of the settings, which also lists every account with what it
stores and carries the pending access requests. That section sits behind `require_admin`: a member
neither sees it nor can call its routes.

`FRONTEND_URL` (defaults to `http://localhost:8080`) builds the clickable links in the emails; set it
to the app's real address if it's reached from a domain or a LAN address.

`MINIFLUX_WEBHOOK_SECRET` is required: Miniflux signs every webhook call with it
(`X-Miniflux-Signature`), and the API rejects anything that doesn't match rather than trusting
whatever reaches `/webhooks/miniflux`. The compose file wires the same value to both sides.

### Using your own Miniflux

Skip the bundled one with the second compose file:

```bash
docker compose -f docker-compose.yml -f docker-compose.external-miniflux.yml up -d
```

Set `MINIFLUX_BASE_URL`, `MINIFLUX_USERNAME` and `MINIFLUX_PASSWORD` in `.env` to your instance, and in
its Integrations settings point the webhook at `http://lumia-backend-api:8000/webhooks/miniflux` with
the same `MINIFLUX_WEBHOOK_SECRET` (use the address Miniflux can reach the API on if it does not share
a Docker network with Lumia). Feeds already in your Miniflux are listed in Lumia, where you tick the
ones to attach: nothing is copied on the Miniflux side. See
[issue #1](https://github.com/techmefr/lumia/issues/1) for the discussion.

### AI, translation and voices

Everything is per account, under **Réglages → IA et traduction**; there is no instance-wide AI key.

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
- **Voices.** The browser's speech synthesis by default; an account can point text-to-speech at
  OpenAI or a custom OpenAI-compatible speech endpoint instead.

Keys are encrypted at rest (Fernet, `SECRET_ENCRYPTION_KEY`) and the API never returns them: it only
exposes `ai_api_key_set` / `translation_api_key_set`.

## Architecture

Monorepo, OSDD (`technical/` / `domain/` split in every app and service; `technical/` never imports
`domain/`).

```
lumia/
├── packages/
│   ├── ui/            Shared Svelte 5 components (primitives, effects, article card)
│   ├── core/          Shared logic and API client
│   └── create-lumia/  Setup CLI (init, doctor, up)
├── apps/
│   ├── web/           SvelteKit SPA
│   ├── mobile/        Svelte + Capacitor (iOS/Android)
│   ├── extension/     WebExtension (Chrome/Firefox)
│   └── auto/          Android Auto (Kotlin, audio only)
├── backend/
│   ├── api/           FastAPI
│   └── worker/        Python enrichment pipeline (TF-IDF, FR/EN stemming, extractive summary)
└── landing/           Static landing page, deployed to GitHub Pages
```

Stack: FastAPI, PostgreSQL, Redis, arq, Miniflux for ingestion, SvelteKit + Svelte 5 + Tailwind 4 on
the front. Keyword extraction and summarization are local — no external AI call is required to read.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown and [CONTRIBUTING.md](CONTRIBUTING.md)
to contribute.

## Development

```bash
pnpm install
pnpm --filter web dev                  # front on :5173, against the API on :8000
VITE_DEMO=true pnpm --filter web dev   # the seeded demo, no backend needed
pnpm --filter web check                # svelte-check
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

Six suites, each with its own coverage floor enforced in CI, plus end-to-end journeys:

```bash
uv run pytest                                # backend, from backend/
pnpm --filter @lumia/core test:coverage      # shared API contracts and http client
pnpm --filter @lumia/ui test:coverage        # design system components
pnpm --filter web test:coverage              # app stores, routes, i18n, demo client
pnpm --filter extension test:coverage        # browser extension
pnpm --filter create-lumia test:coverage     # setup CLI
pnpm --filter web test:e2e                   # Playwright journeys and axe checks on the demo build
```

The floors are ratchets, not targets: 80% is the target everywhere. Raise a floor when you add tests;
never lower one to turn a red run green. See [CONTRIBUTING.md](CONTRIBUTING.md) for how the tests are
written.

### Continuous integration

`.github/workflows/ci.yml` runs on every pull request and every push to `main`:

- **frontend** — `svelte-check`, the core, ui and web suites with their coverage floors, and the
  extension and create-lumia CLI checked, tested and built
- **e2e** — the Playwright journeys and accessibility checks against the demo build
- **backend** — ruff, ruff format, mypy, pytest with its coverage floor, against a real PostgreSQL
- **migrations** — `alembic upgrade head` on an empty database, down to `base` and back up, then
  `alembic check` so the models and the migrations agree
- **docker** — the `lumia-backend` and `lumia-web` images build
- **audit** — known vulnerabilities in the frontend and backend dependencies

Once CI is green on `main`, `release.yml` publishes the `lumia-backend` and `lumia-web` images for
amd64 and arm64 to GitHub Container Registry (`edge` follows `main`, version tags get semver tags),
and `pages.yml` deploys the landing page and the demo.

## License

[AGPL-3.0](LICENSE).
