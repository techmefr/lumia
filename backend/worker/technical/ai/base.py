from typing import Protocol

SUMMARY_PROMPT = (
    "Résume cet article en trois phrases maximum, dans la langue de l'article. "
    "Ne commence pas par « Cet article » et n'ajoute aucun commentaire."
)
# Long articles blow the context window and the bill for no gain: the opening of a piece
# carries its subject.
MAX_INPUT_CHARS = 12_000
TIMEOUT_SECONDS = 60.0


class LlmApiError(Exception):
    pass


class Summarizer(Protocol):
    async def summarize(self, text: str) -> str: ...


class ChatClient(Protocol):
    """A configured LLM reachable with a system prompt and a user message.

    Narrower than a provider SDK on purpose: it is the only shape the callers need, so a second
    use of the account's model — translating, for instance — costs a prompt rather than a client.
    """

    async def complete(self, *, system: str, user: str) -> str: ...

    async def summarize(self, text: str) -> str: ...
