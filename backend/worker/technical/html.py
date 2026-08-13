from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return " ".join(" ".join(self._chunks).split())


def strip_html(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


class _FirstImageExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.src: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.src is not None or tag != "img":
            return
        for name, value in attrs:
            if name == "src" and value:
                self.src = value
                return


def extract_first_image(html: str) -> str | None:
    parser = _FirstImageExtractor()
    parser.feed(html)
    return parser.src
