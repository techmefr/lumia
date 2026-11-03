<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/brand/lumia-logo-dark.avif" />
    <img src="docs/brand/lumia-logo-light.avif" alt="Lumia" width="340" />
  </picture>
</p>

<h3 align="center">Éclaircis tes flux. Apprends tes goûts.</h3>

<p align="center">
  Un lecteur RSS auto-hébergé qui ne garde que l'article, le résume, te le lit à voix haute<br />
  et apprend ce que tu aimes, sans envoyer tes lectures nulle part.
</p>

<p align="center">
  <a href="https://techmefr.github.io/lumia/app/"><strong>Essayer la démo</strong></a> ·
  <a href="#prérequis">Prérequis</a> ·
  <a href="#installation">Installation</a> ·
  <a href="https://techmefr.github.io/lumia/">Page de présentation</a> ·
  <a href="README.md">English version</a>
</p>

<p align="center">
  <a href="https://github.com/techmefr/lumia/actions/workflows/ci.yml"><img src="https://github.com/techmefr/lumia/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/licence-AGPL--3.0-6d63ee" alt="Licence AGPL-3.0" /></a>
  <img src="https://img.shields.io/badge/auto--h%C3%A9berg%C3%A9-docker%20compose-4f46e5" alt="Auto-hébergé avec docker compose" />
  <img src="https://img.shields.io/badge/arch-amd64%20%7C%20arm64-8b85f5" alt="Tourne sur amd64 et arm64" />
  <img src="https://img.shields.io/badge/WCAG-2.2%20AA-a49cf8" alt="WCAG 2.2 AA" />
</p>

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: light)" srcset="docs/screenshots/fr/articles-light.avif" />
    <img src="docs/screenshots/fr/articles-dark.avif" alt="La liste d'articles de Lumia, avec dossiers, flux et cartes d'articles" width="100%" />
  </picture>
</p>

## Pourquoi Lumia

- 🧹 **Juste l'article.** Chaque page est ré-extraite : ni bandeaux, ni menus, ni « vous aimerez
  aussi ».
- ✨ **Il apprend tes goûts.** Tu fais défiler L'Étincelle, et les mots-clés, sources et auteurs que
  tu aimes remontent en tête.
- 🎧 **Écoute au lieu de lire.** Synthèse vocale par article ou sur toute une playlist, calibrée sur
  le temps que tu as, et les podcasts dans le même lecteur.
- 📍 **Reprends où tu t'es arrêté.** La position de lecture te suit du portable au téléphone.
- 🔒 **Tes lectures restent chez toi.** Résumés et mots-clés sont calculés en local ; une clé d'IA
  est facultative.
- 📥 **Fais tout entrer.** OPML Feedly, Mastodon, Bluesky, Reddit, YouTube, Google News,
  newsletters, ou n'importe quelle page enregistrée par URL.
- 📱 **Sur tous les écrans.** Web app installable, extension de navigateur, et ton lecteur habituel
  via l'API Fever.

## Captures d'écran

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/fr/reader-dark.avif" alt="Vue de lecture avec mots-clés, export, traduction et écoute" /><br /><sub><b>Lecture</b> : texte propre, mots-clés, traduction, écoute, export EPUB ou PDF.</sub></td>
    <td width="50%"><img src="docs/screenshots/fr/etincelle-dark.avif" alt="L'Étincelle, une carte à faire glisser pour aimer, passer, mettre en favori ou garder pour plus tard" /><br /><sub><b>L'Étincelle</b> : fais glisser pour apprendre à Lumia ce que tu aimes.</sub></td>
  </tr>
  <tr>
    <td width="50%"><img src="docs/screenshots/fr/playlists-dark.avif" alt="Playlists avec des files générées de 12, 25 ou 45 minutes" /><br /><sub><b>Playlists</b> : une file remplie pour les 12, 25 ou 45 minutes que tu as.</sub></td>
    <td width="50%" align="center"><img src="docs/screenshots/fr/mobile-dark.avif" alt="Lumia sur téléphone, avec la barre de navigation en bas" width="300" /><br /><sub><b>Mobile</b> : PWA installable avec navigation en bas d'écran.</sub></td>
  </tr>
</table>

## L'essayer en 10 secondes

La [démo en ligne](https://techmefr.github.io/lumia/app/) est le vrai front qui tourne sur des
articles fictifs : pas de compte, pas de backend, rien ne sort de ton navigateur. Ouvre un article,
fais défiler L'Étincelle, écoute une playlist ; le bouton « Réinitialiser » de la bannière la remet à
zéro.

## Prérequis

Lumia tourne en sept conteneurs : l'app web, l'API, le worker, PostgreSQL, Redis, et Miniflux avec
son propre PostgreSQL.

| | Minimum | Confortable |
| --- | --- | --- |
| **Machine** | N'importe quel hôte Linux x86_64 ou ARM64 : un petit VPS, un NAS, un Raspberry Pi 4 ou 5 | Un serveur maison ou un VPS 2 vCPU |
| **Mémoire** | 2 Go au total : Lumia lui-même utilise environ 0,6 Go au repos et 1,1 Go en pic | 4 Go, de la marge pour le système et le build |
| **CPU** | 1 cœur | 2 cœurs, pour les pics quand beaucoup de nouveaux articles arrivent d'un coup |
| **Disque** | 5 Go : environ 1,5 Go d'images, le cache de build et la base | 20 Go ou plus ; un article occupe environ 55 Ko en base |
| **Logiciel** | Docker Engine avec Compose v2.24 ou plus récent | |
| **Réseau** | Un accès internet sortant pour récupérer les flux | Un domaine et du HTTPS si tu lis hors de chez toi |

Ces chiffres ont été mesurés sur la stack complète avec 25 vrais flux : environ 600 Mo de mémoire au repos, 1,1 Go pendant l'enrichissement de 272 nouveaux articles d'un coup, et une base de 15 Mo pour ces 272 articles. Pendant un tel pic, le worker prend tous les cœurs disponibles ; sur un seul cœur, le même pic prend simplement plus de temps.

**Ports.** L'app répond sur `8080`. L'API (`8000`) et Miniflux (`8090`) ne sont publiés que sur
l'interface locale ; PostgreSQL, Redis et le worker ne sont jamais publiés.

**Facultatif, jamais obligatoire :**

| Pour avoir | Il te faut |
| --- | --- |
| Les emails (connexion sans mot de passe, réinitialisation, invitations, digest) | Un compte SMTP |
| Les résumés, le chat et les suggestions de tags par IA | Une clé d'API Mistral, OpenAI, Anthropic ou Google, ou ton propre endpoint (Ollama, vLLM, llama.cpp…) |
| La traduction | Une clé DeepL, ou la clé d'IA ci-dessus |
| Des voix naturelles | Un endpoint de synthèse vocale compatible OpenAI ; les voix du navigateur marchent sans rien |

Sans rien de tout ça, Lumia lit, extrait, résume, classe et lit à voix haute tout seul.

## Installation

```bash
git clone https://github.com/techmefr/lumia.git
cd lumia
cp .env.example .env
```

Remplace chaque `change-me` dans `.env`. Deux d'entre eux ont un format imposé :

```bash
openssl rand -hex 32    # JWT_SECRET, POSTGRES_PASSWORD, MINIFLUX_PASSWORD, MINIFLUX_WEBHOOK_SECRET
python3 -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"    # SECRET_ENCRYPTION_KEY
```

Laisse `DEEPL_API_KEY` vide si tu n'en as pas, et les lignes `SMTP_*` telles quelles si tu n'envoies
pas d'emails. Démarre ensuite la stack et crée le schéma de la base :

```bash
docker compose up -d --build
docker compose exec lumia-backend-api alembic upgrade head
```

Le premier build prend quelques minutes. Ouvre **http://localhost:8080** : l'app te guide pour créer
le compte admin et fixer les limites de l'instance, puis tu importes un fichier OPML ou ajoutes tes
premiers flux. Depuis un téléphone ou une tablette du même réseau, utilise l'adresse de la machine
plutôt que `localhost`.

Le CLI [`create-lumia`](packages/create-lumia/README.md) s'occupe du `.env` depuis un clone : `init`
l'écrit avec des secrets générés, `doctor` vérifie Docker, les ports et `.env`, et `up` démarre la
stack.

### Mise à jour

```bash
git pull
docker compose up -d --build
docker compose exec lumia-backend-api alembic upgrade head
```

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
- **Synthèse vocale**, par article ou sur une playlist entière, et les **épisodes de podcast** joués
  dans le même lecteur persistant, diffusés depuis l'hébergeur du flux.
- **Surlignages et notes** sur des passages, regroupés sur leur propre page.
- **Interroger l'article** : un chat sur l'article affiché, via ton propre fournisseur d'IA.
- **Traduction** des articles en langue étrangère, via DeepL ou ton fournisseur d'IA, avec un bouton
  pour revenir à l'original.

### Organisation

- **Lu/non-lu** avec compteurs par flux et par dossier, filtre « non lus seulement », et
  « tout marquer comme lu » sur un flux, un dossier, une liste d'articles explicite ou toute la
  bibliothèque — l'API exige exactement un périmètre, pour qu'un filtre oublié ne marque pas toute
  la bibliothèque comme lue par accident, et marquer toute la bibliothèque demande confirmation
  au-delà de dix articles non lus.
- **Dossiers** renommables et supprimables ; supprimer un dossier laisse ses flux en place, ils
  passent simplement « sans dossier ». Les flux peuvent être renommés et déplacés.
- **Recherche** sur le titre, le résumé et le contenu, combinable avec les filtres
  dossier/flux/auteur/mot-clé, et **recherches enregistrées** qui déclenchent une **alerte** quand un
  nouvel article correspond.
- **Tags** personnels sur n'importe quel article, avec des suggestions par IA quand une clé est
  configurée.
- **Playlists** — des files d'articles ordonnées avec leur durée totale, réordonnables, écoutables
  d'un bout à l'autre, ou générées pour les 12, 25 ou 45 minutes que tu as.
- **Exports** — un article ou une playlist en JSON ou EPUB, et en PDF via la boîte d'impression du
  navigateur.
- **Liens de partage publics** pour un article.
- **Statistiques** sur tes lectures, et un **digest par email** (sur demande) de tes meilleurs
  articles non lus.

### Faire entrer les articles

- **Import OPML** (un export Feedly fonctionne tel quel) : un dossier par catégorie, chaque flux
  enregistré auprès de Miniflux.
- **Ajout d'un flux par URL**, avec le vrai titre du flux résolu à la source.
- **Sources sociales, via leur RSS public** : colle un profil ou un hashtag Mastodon, un profil
  Bluesky, un subreddit ou un utilisateur Reddit, une chaîne YouTube, ou une recherche Google News
  (ou une forme courte comme `r/python`, `@user@mastodon.social`, `#tag@mastodon.social`,
  `@alice.bsky.social`, `news:climate`). Ni clé d'API ni compte nécessaires. Reddit est interrogé
  avec un User-Agent honnête et Miniflux ralentit sur 429/Retry-After ; son RSS public est destiné à
  un usage personnel non commercial, garde-le pour tes propres lectures.
- **Newsletters** sans serveur mail : chaque lecteur reçoit une adresse de réception secrète, et
  n'importe quel transfert capable de poster du JSON y dépose les numéros comme des articles.
- **Enregistrement de n'importe quelle page par URL**, à la Pocket, depuis l'app ou l'extension de
  navigateur : la page est extraite et rangée dans un flux « Enregistrés » propre à l'utilisateur.
  Ré-enregistrer la même URL renvoie l'article existant au lieu de le dupliquer.

### Apprentissage

- **L'Étincelle** — un score de pertinence appris de tes votes, appliqué aux mots-clés, aux sources,
  aux auteurs et aux catégories. Glisse à droite pour aimer, à gauche pour passer, vers le haut pour
  mettre en favori, vers le bas pour garder à lire.
- Les retours sont découpés en axes indépendants : avis (j'aime/je n'aime pas), à lire, favori, lu.

### Autres clients et intégrations

- **Extension de navigateur** pour Chrome et Firefox : enregistre la page courante ou un lien, et lis
  dans le panneau latéral.
- **API Fever**, pour que Reeder, NetNewsWire, Fiery Feeds ou ReadKit se synchronisent avec Lumia.
- **Webhooks sortants**, signés, sur les articles enregistrés, mis en favori ou ajoutés à une
  playlist.
- **App mobile** (Capacitor, iOS et Android) et **Android Auto** (audio seulement) dans
  [`apps/mobile`](apps/mobile/README.md) et [`apps/auto`](apps/auto/README.md).

### Comptes et sécurité

- Onboarding admin au premier lancement, puis comptes sur **invitation** ou demande d'accès, dans
  les quotas de comptes et de disque de l'instance.
- **Connexion sans mot de passe** par email, **double authentification** (TOTP, avec codes de
  secours), et révocation de toutes les sessions depuis les réglages.
- Les clés d'IA et de traduction sont propres à chaque compte, chiffrées en base, et jamais
  renvoyées par l'API.

### Interface

- Raccourcis clavier : `j`/`k` naviguer, `o` ouvrir, `m` lu/non lu, `s` à lire, `u` non lus,
  `f` feuilleter, `/` rechercher, `x` sélectionner, `shift+j`/`shift+k` étendre la sélection,
  `shift+a` tout sélectionner, toujours listés en bas de la liste d'articles.
- Raccourcis de navigation : `g` puis `a` articles, `e` l'Étincelle, `f` flux, `l` à lire,
  `p` playlists, `v` favoris, `t` statistiques, `s` réglages — l'écran d'arrivée prend le focus.
  `?` ouvre la liste complète, et toute touche unique se désactive dans les réglages (WCAG 2.1.4).
- Sept thèmes (clair, sombre, Dracula, Alucard, Nord, Solarized clair et sombre), taille de texte et
  polices de lecture réglables, transitions de page, `prefers-reduced-motion` respecté partout.
- Squelettes de chargement, états vides qui proposent l'action suivante, et notifications avec
  annulation sur les actions destructives.
- WCAG 2.2 AA : lien d'évitement, `aria-current` sur la navigation, régions live sur les états
  asynchrones, groupes de radios natifs plutôt que des imitations ARIA, et une palette vérifiée par
  contraste mesuré plutôt qu'à l'œil. Voir [docs/accessibility.md](docs/accessibility.md).

## Auto-hébergement en détail

L'API expose `GET /health` (le process répond, aucune I/O) et `GET /ready` (PostgreSQL et Redis
répondent, sinon `503` en disant lequel est tombé). Chaque service du compose a un healthcheck bâti
dessus, et l'API, le worker et le conteneur web attendent que leurs dépendances soient *saines* et
plus seulement démarrées — branche ta supervision sur `/health`.

Le conteneur web sert le build statique derrière nginx et relaie `/api` vers l'API, donc l'app
fonctionne depuis n'importe quelle adresse sans configuration ni CORS. Mets `LUMIA_API_BIND=0.0.0.0`
dans `.env` pour joindre l'API elle-même depuis une autre machine, avec `TRUST_PROXY_HEADERS=false`.

`ADMIN_EMAIL`, `ADMIN_USERNAME` et `ADMIN_PASSWORD` court-circuitent l'écran d'onboarding : le compte
administrateur est créé au premier démarrage qui trouve le schéma en place (donc après les
migrations, au redémarrage suivant), et un redémarrage ultérieur n'en crée pas un second ni ne
réécrit son mot de passe. `MAX_ACCOUNTS` et `ACCOUNT_QUOTA_MB` ne donnent que les valeurs initiales
des quotas : ensuite l'administrateur est maître des deux nombres, depuis la section Administration
des réglages, qui liste aussi chaque compte avec son occupation disque et porte les demandes d'accès
en attente. Cette section est derrière `require_admin` : un membre ne la voit pas et ne peut pas
appeler ses routes.

`FRONTEND_URL` (par défaut `http://localhost:8080`) construit les liens cliquables des emails ; à
renseigner avec l'adresse réelle de l'app si elle est jointe par un domaine ou une adresse LAN.

`MINIFLUX_WEBHOOK_SECRET` est obligatoire : Miniflux signe chaque appel de webhook avec
(`X-Miniflux-Signature`), et l'API rejette tout ce qui ne correspond pas plutôt que de faire
confiance à ce qui arrive sur `/webhooks/miniflux`. Le compose relie la même valeur aux deux côtés.

### Utiliser ton propre Miniflux

Passe le Miniflux fourni avec le second fichier compose :

```bash
docker compose -f docker-compose.yml -f docker-compose.external-miniflux.yml up -d
```

Renseigne `MINIFLUX_BASE_URL`, `MINIFLUX_USERNAME` et `MINIFLUX_PASSWORD` dans `.env` avec ton
instance, et dans ses réglages Integrations, pointe le webhook sur
`http://lumia-backend-api:8000/webhooks/miniflux` avec le même `MINIFLUX_WEBHOOK_SECRET` (utilise
l'adresse à laquelle Miniflux joint l'API s'il ne partage pas de réseau Docker avec Lumia). Les flux
déjà présents dans ton Miniflux sont listés dans Lumia, tu coches ceux à rattacher : rien n'est copié
côté Miniflux. Voir [l'issue #1](https://github.com/techmefr/lumia/issues/1) pour la discussion.

### IA, traduction et voix

Tout se règle par compte, dans **Réglages → IA et traduction** ; il n'y a pas de clé d'IA au niveau
de l'instance.

- **Résumé.** Sans clé, le résumé est extractif et calculé localement. Avec une clé, il passe par un
  modèle : Mistral, OpenAI, Anthropic, Gemma (l'endpoint compatible OpenAI de Google), ou un
  endpoint personnalisé — vLLM, Ollama, llama.cpp, Voxtral, un Gemma en local, n'importe quoi qui
  parle le format `/chat/completions`. L'endpoint personnalisé demande l'URL et le nom du modèle,
  qu'on ne peut pas deviner. Un provider injoignable ou une clé refusée ne coûte pas son résumé à
  l'article : on retombe sur l'extractif.
- **Traduction.** D'abord la clé DeepL du compte, puis l'IA que le compte a configurée, puis le
  `DEEPL_API_KEY` de l'instance — selon ce qui est réellement configuré. `DEEPL_API_KEY` est
  facultatif : une instance avec une clé IA et sans DeepL traduit via le modèle, et une instance
  sans aucune clé garde les articles dans leur langue au lieu d'échouer sur chacun. Les articles
  sont traduits vers la « langue de lecture » du compte à leur arrivée, et la page article porte un
  bouton pour traduire l'article affiché dans la langue de l'interface et revenir à l'original.
- **Voix.** La synthèse vocale du navigateur par défaut ; un compte peut brancher la lecture à voix
  haute sur OpenAI ou sur un endpoint de synthèse vocale compatible OpenAI.

Les clés sont chiffrées en base (Fernet, `SECRET_ENCRYPTION_KEY`) et l'API ne les renvoie jamais :
elle expose seulement `ai_api_key_set` / `translation_api_key_set`.

## Architecture

Monorepo, OSDD (séparation `technical/` / `domain/` dans chaque app et service ; `technical/`
n'importe jamais `domain/`).

```
lumia/
├── packages/
│   ├── ui/            Composants Svelte 5 partagés (primitives, effets, carte d'article)
│   ├── core/          Logique partagée et client d'API
│   └── create-lumia/  CLI d'installation (init, doctor, up)
├── apps/
│   ├── web/           SPA SvelteKit
│   ├── mobile/        Svelte + Capacitor (iOS/Android)
│   ├── extension/     WebExtension (Chrome/Firefox)
│   └── auto/          Android Auto (Kotlin, audio seulement)
├── backend/
│   ├── api/           FastAPI
│   └── worker/        Pipeline d'enrichissement Python (TF-IDF, racinisation FR/EN, résumé extractif)
└── landing/           Page de présentation statique, déployée sur GitHub Pages
```

Stack : FastAPI, PostgreSQL, Redis, arq, Miniflux pour l'ingestion, SvelteKit + Svelte 5 +
Tailwind 4 côté front. L'extraction de mots-clés et le résumé sont locaux — aucun appel à une IA
externe n'est nécessaire pour lire.

Voir [ARCHITECTURE.md](ARCHITECTURE.md) pour le détail complet et [CONTRIBUTING.md](CONTRIBUTING.md)
pour contribuer.

## Développement

```bash
pnpm install
pnpm --filter web dev                  # front sur :5173, contre l'API sur :8000
VITE_DEMO=true pnpm --filter web dev   # la démo seedée, sans backend
pnpm --filter web check                # svelte-check
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
`postgresql+asyncpg://lumia:lumia@localhost:55432/lumia_test` et `redis://localhost:6379/1`, que
deux conteneurs jetables fournissent :

```bash
docker run -d --name lumia-test-db -p 55432:5432 -e POSTGRES_USER=lumia -e POSTGRES_PASSWORD=lumia -e POSTGRES_DB=lumia_test postgres:16-alpine
docker run -d --name lumia-test-redis -p 6379:6379 redis:7-alpine
```

### Tests et couverture

Six suites, chacune avec son plancher de couverture vérifié en CI, plus des parcours de bout en bout :

```bash
uv run pytest                                # backend, depuis backend/
pnpm --filter @lumia/core test:coverage      # contrats d'API et client http partagés
pnpm --filter @lumia/ui test:coverage        # composants du design system
pnpm --filter web test:coverage              # stores, routes, i18n, client de démo
pnpm --filter extension test:coverage        # extension de navigateur
pnpm --filter create-lumia test:coverage     # CLI d'installation
pnpm --filter web test:e2e                   # parcours Playwright et contrôles axe sur le build de démo
```

Les planchers sont des crans, pas des objectifs : la cible est 80 % partout. On relève un plancher
quand on ajoute des tests ; on ne l'abaisse jamais pour faire passer une CI rouge. Voir
[CONTRIBUTING.md](CONTRIBUTING.md) pour la façon dont les tests sont écrits.

### Intégration continue

`.github/workflows/ci.yml` tourne sur chaque pull request et chaque push sur `main` :

- **frontend** — `svelte-check`, les suites core, ui et web avec leurs planchers, et l'extension et
  le CLI create-lumia vérifiés, testés et construits
- **e2e** — les parcours Playwright et les contrôles d'accessibilité sur le build de démo
- **backend** — ruff, ruff format, mypy, pytest avec son plancher, contre un vrai PostgreSQL
- **migrations** — `alembic upgrade head` sur une base vide, retour à `base` et remontée, puis
  `alembic check` pour que les modèles et les migrations concordent
- **docker** — les images `lumia-backend` et `lumia-web` se construisent
- **audit** — les vulnérabilités connues des dépendances front et back

Une fois la CI verte sur `main`, `release.yml` publie les images `lumia-backend` et `lumia-web` pour
amd64 et arm64 sur le GitHub Container Registry (`edge` suit `main`, les tags de version reçoivent
des tags semver), et `pages.yml` déploie la page de présentation et la démo.

## Licence

[AGPL-3.0](LICENSE).
