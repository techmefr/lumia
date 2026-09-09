# Lumia

> Éclaircis tes flux. Apprends tes goûts.

Lumia est un lecteur RSS auto-hébergé. Il récupère tes flux, nettoie les articles de tout ce qui
n'est pas l'article, en extrait les mots-clés et un résumé, puis apprend ce qui t'intéresse au fil de
tes lectures. Tout tourne sur ta propre machine.

**[Page de présentation](https://techmefr.github.io/lumia/)** ·
**[Démo en ligne](https://techmefr.github.io/lumia/app/)** ·
English version: [README.md](README.md)

La démo est le vrai front, avec le client http remplacé par un client en mémoire alimenté par des
articles fictifs. Rien ne sort du navigateur, il n'y a ni compte ni backend derrière ; le bouton
« Réinitialiser » de la bannière remet l'état seedé à zéro. Elle sert à juger l'interface, la vue de
lecture et la synthèse vocale sur un vrai appareil avant d'installer quoi que ce soit.

## Ce que ça fait

### Lecture

- **Articles complets et lisibles.** Chaque page est re-téléchargée et re-extraite avec
  [trafilatura](https://trafilatura.readthedocs.io) pour retirer menus, bandeaux et listes
  d'articles connexes. L'extraction du crawler de flux laisse régulièrement passer le décor du site
  dans le corps de l'article.
- **Temps de lecture estimé** sur chaque carte, calculé sur le nombre de mots.
- **Position de lecture enregistrée côté serveur.** On rouvre un article sur un autre appareil et on
  repart où on s'était arrêté. La position ne recule jamais : un passage rapide qui atterrit en haut
  de page n'effacera pas la progression.
- **Barre de progression** en haut de l'article, et au-delà de 90 % lu l'article se marque lu
  tout seul.
- **Synthèse vocale**, par article ou sur une playlist entière.

### Organisation

- **Lu/non-lu** avec compteurs par flux et par dossier, filtre « non lus seulement », et
  « tout marquer comme lu » sur un flux, un dossier ou une liste d'articles explicite — l'API exige
  exactement un périmètre, pour qu'un filtre oublié ne marque pas toute la bibliothèque comme lue.
- **Dossiers** renommables et supprimables ; supprimer un dossier laisse ses flux en place, ils
  passent simplement « sans dossier ». Les flux peuvent être renommés et déplacés.
- **Recherche** sur le titre, le résumé et le contenu, combinable avec les filtres
  dossier/flux/auteur/mot-clé.
- **Playlists** — des files d'articles ordonnées avec leur durée totale, réordonnables, écoutables
  d'un bout à l'autre.
- **Pagination** sur toutes les listes, 24 articles à la fois.

### Faire entrer les articles

- **Import OPML** (un export Feedly fonctionne tel quel) : un dossier par catégorie, chaque flux
  enregistré auprès de Miniflux.
- **Ajout d'un flux par URL**, avec le vrai titre du flux résolu à la source.
- **Enregistrement de n'importe quelle page par URL**, à la Pocket : la page est extraite et rangée
  dans un flux « Enregistrés » propre à l'utilisateur. Ré-enregistrer la même URL renvoie l'article
  existant au lieu de le dupliquer.
- **Traduction** des articles en langue étrangère (DeepL).

### Apprentissage

- **L'Étincelle** — un score de pertinence appris de tes votes, appliqué aux mots-clés, aux sources,
  aux auteurs et aux catégories. Glisse à droite pour aimer, à gauche pour passer.
- Les retours sont découpés en axes indépendants : avis (j'aime/je n'aime pas), à lire, favori, lu.

### Interface

- Raccourcis clavier : `j`/`k` naviguer, `o` ouvrir, `m` lu/non lu, `s` à lire, `u` non lus,
  `/` rechercher.
- Squelettes de chargement, états vides qui proposent l'action suivante, et notifications avec
  annulation sur les actions destructives.
- Clair/sombre, taille de texte réglable, transitions de page, `prefers-reduced-motion` respecté
  partout.
- WCAG 2.2 AA : lien d'évitement, `aria-current` sur la navigation, régions live sur les états
  asynchrones, groupes de radios natifs plutôt que des imitations ARIA, et une palette vérifiée par
  contraste mesuré plutôt qu'à l'œil.

## Architecture

Monorepo, OSDD (séparation `technical/` / `domain/` dans chaque app et service ; `technical/`
n'importe jamais `domain/`).

```
lumia/
├── packages/
│   ├── ui/       Composants Svelte 5 partagés (primitives, effets, carte d'article)
│   └── core/     Logique partagée (feed, article, user, recommendation, playlist)
├── apps/
│   ├── web/          SPA SvelteKit
│   ├── mobile/       Svelte + Capacitor (iOS/Android) — prévu
│   ├── extension/    WebExtension (Chrome/Firefox) — prévu
│   └── auto/         Android Auto (Kotlin, audio seulement) — prévu
├── backend/
│   ├── api/       FastAPI
│   └── worker/    Pipeline d'enrichissement Python (TF-IDF, racinisation FR/EN, résumé extractif)
└── landing/       Page de présentation statique, déployée sur GitHub Pages
```

Stack : FastAPI, PostgreSQL, Redis, arq, Miniflux pour l'ingestion, SvelteKit + Svelte 5 +
Tailwind 4 côté front. L'extraction de mots-clés et le résumé sont locaux — aucun appel à une IA
externe n'est nécessaire pour lire.

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le détail complet et [CONTRIBUTING.md](CONTRIBUTING.md)
pour contribuer.

## Auto-hébergement

```bash
git clone https://github.com/techmefr/lumia.git
cd lumia
cp .env.example .env    # puis renseigne les secrets
docker compose up -d
```

L'app répond sur `http://localhost:8080`, l'API sur `http://localhost:8000`. Seuls ces deux-là sont
exposés ; Miniflux, le worker, PostgreSQL et Redis restent sur le réseau interne. Le conteneur web
sert le build statique derrière nginx et relaie `/api` vers l'API, donc l'app fonctionne depuis
n'importe quelle adresse sans configuration ni CORS. Au premier lancement, l'app déroule l'onboarding admin : compte administrateur,
limites de l'instance (nombre de comptes, quota disque par utilisateur), puis tu peux importer un
OPML ou ajouter des flux.

Pour y accéder depuis un téléphone ou une tablette du même réseau, utilise l'adresse locale de la
machine, pas `localhost`. La [page de présentation](https://techmefr.github.io/lumia/) sait retenir
cette adresse par appareil et te donne un bouton direct.

### Migrations de base

```bash
docker compose exec lumia-backend-api uv run alembic upgrade head
```

## Développement

```bash
pnpm install
pnpm --filter web dev      # front sur :5173
pnpm --filter web check    # svelte-check
pnpm --filter web build
```

Backend, depuis `backend/` :

```bash
uv sync --all-groups
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

La suite backend a besoin de PostgreSQL et Redis accessibles. Elle vise par défaut
`postgresql+asyncpg://lumia:lumia@localhost:55432/lumia_test`, qu'un conteneur jetable fournit :

```bash
docker run -d --name lumia-test-db -p 55432:5432 -e POSTGRES_USER=lumia -e POSTGRES_PASSWORD=lumia -e POSTGRES_DB=lumia_test postgres:16-alpine
```

### Tests et couverture

Quatre suites, chacune avec son plancher de couverture vérifié à chaque push :

```bash
uv run pytest                             # backend, depuis backend/
pnpm --filter @lumia/core test:coverage   # contrats d'api et client http partagés
pnpm --filter @lumia/ui test:coverage     # composants du design system
pnpm --filter web test:coverage           # stores de l'app, i18n, client de démo
```

| Suite            | Tests | Couverture | Plancher |
| ---------------- | ----- | ---------- | -------- |
| `backend`        | 312   | 86 %       | 80 %     |
| `packages/core`  | 108   | 100 %      | 80 %     |
| `packages/ui`    | 31    | 21 %       | 21 %     |
| `apps/web`       | 226   | 16 %       | 15 %     |

Les deux planchers du front sont des crans, pas des objectifs : la cible est 80 % partout, et ce
qui manque, ce sont les écrans et les pages de route, encore sans tests. On relève un plancher quand
on ajoute des tests ; on ne l'abaisse jamais pour faire passer une CI rouge. Voir
[CONTRIBUTING.md](CONTRIBUTING.md) pour la façon dont les tests sont écrits.

### Intégration continue

`.github/workflows/ci.yml` tourne à chaque push et chaque pull request :

- **frontend** — `svelte-check`, puis les trois suites vitest avec leurs planchers
- **backend** — ruff, ruff format, mypy, pytest avec son plancher, contre un vrai PostgreSQL
- **migrations** — `alembic upgrade head` sur une base vide, puis retour à `base` et remontée, pour
  qu'une version puisse être annulée puis réappliquée
- **docker** — l'image du backend se construit

## Clés d'IA et de traduction

Tout se règle par compte, dans **Réglages → IA et traduction** ; il n'y a pas de clé au niveau de
l'instance.

- **Résumé.** Sans clé, le résumé est extractif et calculé localement. Avec une clé, il passe par un
  modèle : Mistral, OpenAI, ou n'importe quel endpoint compatible OpenAI (vLLM, Ollama, Voxtral) —
  ces derniers demandent l'URL et le nom du modèle, qu'on ne peut pas deviner. Un provider
  injoignable ou une clé refusée ne coûte pas son résumé à l'article : on retombe sur l'extractif.
- **Traduction.** Une clé DeepL par compte, sinon le `DEEPL_API_KEY` de l'instance en secours. La
  langue cible est la « langue de lecture » du compte.

Les clés sont chiffrées en base (Fernet, `SECRET_ENCRYPTION_KEY`) et l'API ne les renvoie jamais :
elle expose seulement `ai_api_key_set` / `translation_api_key_set`.

## Licence

[AGPL-3.0](LICENSE).
