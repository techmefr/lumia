# Architecture

## Monorepo layout

Every app and service follows OSDD: a `technical/` folder for cross-cutting concerns (auth, HTTP, storage, DB, middleware) and a `domain/` folder for business logic, split into bounded contexts.

```
lumia/
├── packages/
│   ├── ui/              Shared Svelte components
│   │   ├── technical/   Inputs, skeletons, layouts
│   │   └── domain/      ArticleCard, FlashCard, OrbitButton
│   └── core/             Shared logic
│       ├── technical/   Auth, HTTP, storage, config
│       └── domain/      feed/, article/, user/, recommendation/, audio/
│
├── apps/
│   ├── web/              Svelte SPA
│   ├── mobile/           Svelte + Capacitor (iOS + Android)
│   ├── extension/        WebExtension (Chrome + Firefox)
│   │   ├── popup/        Quick-save (Pocket-style)
│   │   └── sidepanel/    Full reader
│   └── auto/             Android Auto (Kotlin, audio only)
│       └── MediaBrowserService talks to the same FastAPI backend
│
└── backend/              Single deployable unit: lumia-backend
    ├── api/              FastAPI
    │   ├── technical/    Auth, sessions, middleware, DB
    │   └── domain/       feed/, article/, user/, recommendation/, audio/
    └── worker/           Ingestion + enrichment pipeline (arq jobs)
        ├── technical/    Source connectors, webhook, queue, DB client
        └── domain/       extraction/, scoring/, summarizer/
```

`technical/` never imports from `domain/` in a different bounded context; `domain/` never reaches into another app's `domain/` directly — shared behavior lives in `packages/core`.

`api/` and `worker/` are two application layers in the same codebase and the same Docker image (`lumia-backend`) — the API serves clients, the worker processes background jobs. `docker-compose` runs two containers from that one image with different start commands, rather than publishing two images to maintain separately.

## Source connectors (ingestion)

Every ingestion engine (Miniflux today, mail/social feeds later) implements a `SourceConnector` in `worker/technical/connectors/`: it turns that engine's raw webhook payload into a normalized `RawArticle` before it enters the shared enrichment pipeline in `domain/`. Adding an engine means adding a connector and running its own upstream service (like the `miniflux` container) — the domain pipeline, the API, and the `lumia-backend` image never change.

## Bounded contexts

| Context | Responsibility |
|---|---|
| `feed` | RSS feeds, folders, themes |
| `article` | Enrichment, keywords, extractive summary |
| `user` | Account, preferences, personal AI config |
| `recommendation` | Scoring, L'Étincelle, learning algorithm |
| `audio` | TTS queue, available-time scheduling |

## Pipeline

```
Engine (Miniflux polls RSS every N minutes, others later)
  │
  └─ Webhook POST → lumia-backend worker
        │
        ├─ SourceConnector: raw payload → RawArticle
        ├─ TF-IDF keyword extraction (scikit-learn)
        ├─ FR/EN stemming (NLTK / spaCy)
        ├─ Extractive summary (leading significant sentences)
        │
        └─ INSERT PostgreSQL (articles, keywords — no score yet)
              │
              └─ GET /articles → clients (web, mobile, extension)
```

Recommendation scores aren't written at ingestion time — they're learned per user from feedback (like/dislike), see the `recommendation` bounded context.

## Deployment

`lumia-backend` is the one mandatory module (API + worker, one image, two containers). Engines (`miniflux`, …) and frontends (`lumia-web`, …) are optional bricks that feed or consume it. Only `lumia-backend`'s API container and `lumia-web` are exposed publicly; engines, the worker container, Redis, and PostgreSQL stay on the internal Docker network. Auth uses a short-lived JWT access token plus a revocable opaque refresh token (see ADR-0006), sent as an `Authorization: Bearer` header — a bearer token, unlike an httpOnly cookie, works uniformly across the web SPA, the Capacitor mobile app, and the browser extension, which don't share a cookie jar with the API's origin.

## Multi-tenancy

First launch runs a mandatory 3-step admin onboarding (admin account → instance limits → confirmation) before any other access is allowed. Instance-wide settings (max accounts, per-user disk quota) are admin-only; AI provider and API key are per-user, with no instance-wide key.
