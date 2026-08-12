# Lumia

> Clarifie tes flux et apprend tes goûts.

Lumia est un lecteur RSS self-hosted, multi-tenant et communautaire qui apprend ce que tu aimes.

English version: [README.md](README.md)

## Ce que ça fait

Lumia récupère les flux RSS via [Miniflux](https://miniflux.app), enrichit chaque article (extraction de mots-clés, résumé extractif), puis apprend tes préférences à partir de la façon dont tu swipes les articles. Tout tourne sur ta propre infrastructure.

- **Kiosque** — flux organisés par dossiers/thèmes
- **Archive** — articles sauvegardés, vue chronologique ou thématique
- **L'Étincelle** — recommandations triées par pertinence apprise
- **Audio** — file de lecture TTS triée par score et temps disponible (Phase 2)
- **Profil** — compte, thème, taille du texte, configuration du provider IA

## Architecture

Monorepo, OSDD (séparation `technical/` / `domain/` dans chaque app et service).

```
lumia/
├── packages/
│   ├── ui/       Composants Svelte partagés
│   └── core/     Logique partagée (feed, article, user, recommendation, audio)
├── apps/
│   ├── web/          SPA Svelte
│   ├── mobile/       Svelte + Capacitor (iOS/Android)
│   ├── extension/    WebExtension (Chrome/Firefox) : popup + sidepanel
│   └── auto/         Android Auto (Kotlin, audio uniquement)
└── backend/
    ├── api/       FastAPI
    └── worker/    Pipeline Python d'enrichissement TF-IDF
```

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le détail complet et [CONTRIBUTING.md](CONTRIBUTING.md) pour contribuer.

## Self-hosting

Un `docker-compose.yml` de référence est fourni à la racine. Seuls `lumia-api` et `lumia-web` sont exposés publiquement ; Miniflux, le worker et PostgreSQL restent sur le réseau interne. L'authentification passe par un cookie httpOnly — aucun token n'est jamais exposé côté JS.

```bash
docker compose up -d
```

Au premier lancement, l'app guide un onboarding admin : compte administrateur, limites d'instance (nombre max de comptes, quota disque par utilisateur), puis c'est prêt à ajouter des flux.

## Providers IA

Résumés et scoring de recommandation sont configurés par utilisateur : chaque compte choisit son provider (Mistral, OpenAI, ou un endpoint self-hosted type Voxtral) et sa clé API. Aucune clé n'est imposée au niveau de l'instance.

## Licence

[AGPL-3.0](LICENSE).
