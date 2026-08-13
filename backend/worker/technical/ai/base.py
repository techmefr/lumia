from typing import Protocol


class Summarizer(Protocol):
    async def summarize(self, text: str) -> str: ...
