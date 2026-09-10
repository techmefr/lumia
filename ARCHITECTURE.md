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

The worker also runs two scheduled passes of its own (`worker/domain/maintenance/`, registered as
`cron_jobs` in `worker/technical/queue.py`). Reconciliation, on the hour, asks Miniflux for the
entries of the last day and re-queues those missing from the database: a webhook can be lost for
reasons nothing in the app can prevent — the API restarting mid-post, a network blip, a signature
refused after a secret rotation — and it doubles as the recovery for an enrichment that exhausted
its retries. It skips entries of feeds nobody subscribes to, which enrichment would drop anyway.
The nightly purge deletes login tokens well past their expiry, keeping a grace period so a
just-lapsed token is still recognised as expired rather than as never issued.

The Miniflux webhook is signed (`X-Miniflux-Signature`, HMAC-SHA256 over the raw body, checked with
`hmac.compare_digest` in `worker/technical/webhook.py`) against `MINIFLUX_WEBHOOK_SECRET`, which has
no default — the config fails to start without one rather than accepting unsigned calls silently.

Any URL a reader submits — a saved page, a feed added by URL, an OPML entry — is checked by
`api/technical/net/url_guard.py` before the instance requests it: http(s) only, and the host has to
resolve outside the loopback, private, link-local and reserved ranges. The check runs again on every
redirect hop (`fetch_page_html`), because a public URL redirecting to a metadata endpoint would
otherwise walk straight past a first-hop-only guard, and the response body is capped so an endless
one cannot take the process down.

A subscription export is parsed with `defusedxml` (`api/domain/feed/opml_parser.py`) and the upload
is capped before it is read whole (`_read_capped` in `api/domain/feed/routes.py`, 413 over 2 MB):
the stdlib XML parser expands entities, so a few kilobytes of nested ones are otherwise enough to
exhaust the API process.

Passwordless sign-in (`api/domain/user/magic_link_service.py`) issues an opaque token, stores only
its hash (`MagicLinkToken`, single-use, TTL-bound), and emails a clickable
`{FRONTEND_URL}/login?magic_token=...` link built from `EmailConfig.frontend_url`. `/login` reads
that query param on mount and calls `verifyMagicLink` before showing any form — this is also the
app's only account-recovery path, there being no separate forgot-password flow. Asking for a new
link retires the ones already sent, so only one live link exists per reader at any time.

The authentication routes are rate limited (`api/technical/rate_limit/`) with a fixed-window
counter in Redis, keyed on two identifiers at once: the caller's address and the account being
addressed. One alone is not enough — by address only, a botnet walks past the cap; by account only,
an attacker locks a reader out of their own account by burning its allowance. The address is read
from the last `X-Forwarded-For` entry, the one the shipped nginx vouches for, and only when
`TRUST_PROXY_HEADERS` is on. Over the allowance the answer is a 429 carrying `Retry-After`, for the
correct password as much as for a wrong one: a limit that lets the right password through does not
limit what is being guessed.

Beyond the first admin, accounts exist only through an invitation an admin sends
(`api/domain/user/invitation_service.py`): a single-use token, stored hashed like the magic link,
bound to one address and one role, emailed as `{FRONTEND_URL}/invitation?token=...` and redeemed at
`POST /invitations/accept` — the one write route left unauthenticated on purpose, the token being the
only credential the invitee has yet. `Instance.max_accounts` is the ceiling all three creation paths
respect: invitation, acceptance, and SSO provisioning. Pending invitations count against it, so a
seat already promised cannot be promised twice.

Beyond the first admin, accounts exist only through an invitation an admin sends
(): a single-use token, stored hashed like the magic link,
bound to one address and one role, emailed as  and redeemed at
 — the one write route that is unauthenticated on purpose, the token being
the only credential the invitee has yet.  is the ceiling all three creation
paths respect: invitation, acceptance, and SSO provisioning. Pending invitations count against it,
so seats already promised cannot be promised twice.

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
