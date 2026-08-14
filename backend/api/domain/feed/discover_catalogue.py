"""A small curated catalogue of public feeds, used to suggest sources.

Why a static list rather than a live directory: the other candidate pool on a self-hosted instance
would be what the other accounts are subscribed to, which would leak their reading to every user of
the instance. A catalogue shipped with the code leaks nothing and stays auditable.

The `topics` of each entry are matched, in lowercase, against the categories and keywords the reader
has actually voted on, so the ranking says something about them rather than about the catalogue.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogueEntry:
    title: str
    url: str
    site_url: str
    description: str
    language: str
    topics: tuple[str, ...]


CATALOGUE: tuple[CatalogueEntry, ...] = (
    CatalogueEntry(
        title="Le Monde — Pixels",
        url="https://www.lemonde.fr/pixels/rss_full.xml",
        site_url="https://www.lemonde.fr/pixels/",
        description="Numérique, jeux vidéo et cultures en ligne.",
        language="fr",
        topics=("technologie", "numérique", "jeu vidéo", "internet"),
    ),
    CatalogueEntry(
        title="Next",
        url="https://next.ink/feed/",
        site_url="https://next.ink",
        description="Informatique, logiciel libre et politiques du numérique.",
        language="fr",
        topics=("technologie", "logiciel libre", "vie privée", "informatique"),
    ),
    CatalogueEntry(
        title="LinuxFr.org",
        url="https://linuxfr.org/news.atom",
        site_url="https://linuxfr.org",
        description="Actualité du logiciel libre, écrite par ses utilisateurs.",
        language="fr",
        topics=("linux", "logiciel libre", "développement", "auto-hébergement"),
    ),
    CatalogueEntry(
        title="Framablog",
        url="https://framablog.org/feed/",
        site_url="https://framablog.org",
        description="Logiciel libre, communs numériques et décentralisation.",
        language="fr",
        topics=("logiciel libre", "vie privée", "communs", "décentralisation"),
    ),
    CatalogueEntry(
        title="CNRS Le Journal",
        url="https://lejournal.cnrs.fr/rss",
        site_url="https://lejournal.cnrs.fr",
        description="La recherche française racontée par le CNRS.",
        language="fr",
        topics=("science", "recherche", "physique", "biologie"),
    ),
    CatalogueEntry(
        title="Pour la Science",
        url="https://www.pourlascience.fr/rss",
        site_url="https://www.pourlascience.fr",
        description="Vulgarisation scientifique de fond.",
        language="fr",
        topics=("science", "mathématiques", "astronomie", "recherche"),
    ),
    CatalogueEntry(
        title="Étapes",
        url="https://etapes.com/feed/",
        site_url="https://etapes.com",
        description="Design graphique, typographie et culture visuelle.",
        language="fr",
        topics=("design", "typographie", "graphisme", "création"),
    ),
    CatalogueEntry(
        title="Arrêt sur images — Chroniques",
        url="https://api.arretsurimages.net/api/public/rss/all-content",
        site_url="https://www.arretsurimages.net",
        description="Critique des médias et de l'information.",
        language="fr",
        topics=("médias", "information", "société", "politique"),
    ),
    CatalogueEntry(
        title="Hacker News — Front page",
        url="https://hnrss.org/frontpage",
        site_url="https://news.ycombinator.com",
        description="What developers are reading today.",
        language="en",
        topics=("technologie", "développement", "startup", "informatique"),
    ),
    CatalogueEntry(
        title="Julia Evans",
        url="https://jvns.ca/atom.xml",
        site_url="https://jvns.ca",
        description="Systems and networking, explained from first principles.",
        language="en",
        topics=("développement", "linux", "réseau", "debug"),
    ),
    CatalogueEntry(
        title="CSS-Tricks",
        url="https://css-tricks.com/feed/",
        site_url="https://css-tricks.com",
        description="Front-end techniques, layout and browser behaviour.",
        language="en",
        topics=("css", "front-end", "web", "design"),
    ),
    CatalogueEntry(
        title="Quanta Magazine",
        url="https://api.quantamagazine.org/feed/",
        site_url="https://www.quantamagazine.org",
        description="Mathematics, physics and computer science, at length.",
        language="en",
        topics=("science", "mathématiques", "physique", "informatique"),
    ),
    CatalogueEntry(
        title="Low-tech Magazine",
        url="https://solar.lowtechmagazine.com/feeds/all-en.atom.xml",
        site_url="https://solar.lowtechmagazine.com",
        description="Energy, sobriety and technologies that last.",
        language="en",
        topics=("énergie", "environnement", "sobriété", "technologie"),
    ),
    CatalogueEntry(
        title="A Learning a Day",
        url="https://alearningaday.blog/feed/",
        site_url="https://alearningaday.blog",
        description="Short daily notes on work, decisions and habits.",
        language="en",
        topics=("productivité", "management", "apprentissage"),
    ),
    CatalogueEntry(
        title="Nota Bene",
        url="https://nolwennporte.substack.com/feed",
        site_url="https://nolwennporte.substack.com",
        description="Histoire et récits documentés.",
        language="fr",
        topics=("histoire", "culture", "société"),
    ),
)
