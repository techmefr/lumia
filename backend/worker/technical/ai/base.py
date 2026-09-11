from dataclasses import dataclass
from typing import Literal, Protocol

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


Role = Literal["user", "assistant"]


@dataclass(frozen=True)
class Turn:
    role: Role
    content: str


@dataclass(frozen=True)
class ChatAnswer:
    text: str
    #: What the provider itself reported spending, None when it reported nothing. Estimating it
    #: would be worse than saying nothing: a reader deciding whether to ask another question needs
    #: the figure they will be billed on.
    tokens_used: int | None


class ChatClient(Protocol):
    """A configured LLM reachable with a system prompt and a user message.

    Narrower than a provider SDK on purpose: it is the only shape the callers need, so a second
    use of the account's model — translating, for instance — costs a prompt rather than a client.
    """

    async def complete(self, *, system: str, user: str) -> str: ...

    async def summarize(self, text: str) -> str: ...

    async def converse(self, *, system: str, turns: list[Turn]) -> ChatAnswer: ...
