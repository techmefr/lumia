import re

from api.domain.tag.schemas import MAX_TAG_LENGTH, TagSuggestionResponse
from worker.technical.ai.base import MAX_INPUT_CHARS, ChatClient

MAX_AI_SUGGESTIONS = 5

TAG_PROMPT = (
    "Propose au plus cinq étiquettes pour classer cet article dans la bibliothèque d'un lecteur. "
    "Chaque étiquette est un concept court (un à trois mots) dans la langue de l'article, pas "
    "forcément un mot présent dans le texte. Réponds uniquement par les étiquettes, une par ligne, "
    "sans numérotation, sans commentaire."
)

_LIST_MARKER = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


def parse_tag_lines(raw: str, *, excluded: set[str]) -> list[str]:
    """Reads one tag per line, dropping bullets, blanks, repeats and anything the reader has.

    A model asked for a bare list still tends to bullet or number it, so the markers are stripped
    rather than trusted to be absent.
    """
    names: list[str] = []
    seen = set(excluded)
    for line in raw.splitlines():
        name = " ".join(_LIST_MARKER.sub("", line).strip(" \t\"'`#.,;").split())
        if not name or len(name) > MAX_TAG_LENGTH or name.casefold() in seen:
            continue
        seen.add(name.casefold())
        names.append(name)
    return names[:MAX_AI_SUGGESTIONS]


async def suggest_with_ai(
    chat_client: ChatClient, *, title: str, text: str, excluded: set[str]
) -> list[TagSuggestionResponse]:
    answer = await chat_client.complete(
        system=TAG_PROMPT, user=f"{title}\n\n{text[:MAX_INPUT_CHARS]}"
    )
    return [
        TagSuggestionResponse(name=name, source="ai")
        for name in parse_tag_lines(answer, excluded=excluded)
    ]
