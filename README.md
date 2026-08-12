# Lumia

> Clarify your feeds and learn your tastes.

Lumia is a self-hosted, multi-tenant, community-driven RSS reader that learns what you like.

Version française : [README.fr.md](README.fr.md)

## What it does

Lumia ingests RSS feeds through [Miniflux](https://miniflux.app), enriches every article with keyword extraction and extractive summarization, then learns your preferences from the way you swipe through them. Everything runs on your own infrastructure.

- **Kiosque** — feeds organized by folders/themes
- **Archive** — saved articles, chronological or thematic view
- **L'Étincelle** — recommendations ranked by a learned relevance score
- **Audio** — text-to-speech reading queue sorted by score and available time (Phase 2)
- **Profil** — account, theme, text size, AI provider configuration

## Architecture

Monorepo, OSDD (`technical/` / `domain/` split in every app and service).

```
lumia/
├── packages/
│   ├── ui/       Shared Svelte components
│   └── core/     Shared logic (feed, article, user, recommendation, audio)
├── apps/
│   ├── web/          Svelte SPA
│   ├── mobile/        Svelte + Capacitor (iOS/Android)
│   ├── extension/     WebExtension (Chrome/Firefox): popup + sidepanel
│   └── auto/          Android Auto (Kotlin, audio only)
└── backend/
    ├── api/       FastAPI
    └── worker/    Python TF-IDF enrichment pipeline
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full breakdown and [CONTRIBUTING.md](CONTRIBUTING.md) to contribute.

## Self-hosting

A reference `docker-compose.yml` is provided at the repo root. Only `lumia-api` and `lumia-web` are exposed publicly; Miniflux, the worker, and PostgreSQL stay on the internal network. Authentication uses an httpOnly cookie — no token is ever exposed to client-side JS.

```bash
docker compose up -d
```

On first launch, the app walks you through admin onboarding: admin account, instance limits (max accounts, per-user disk quota), then you're ready to add feeds.

## AI providers

Summarization and recommendation scoring are per-user: each account configures its own provider (Mistral, OpenAI, or a custom self-hosted endpoint such as Voxtral) and API key. There is no instance-wide key.

## License

[AGPL-3.0](LICENSE).
