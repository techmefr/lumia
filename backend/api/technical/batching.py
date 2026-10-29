from collections.abc import Iterator, Sequence

MAX_BIND_BATCH = 1000


def chunked[T](items: Sequence[T], size: int = MAX_BIND_BATCH) -> Iterator[Sequence[T]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
