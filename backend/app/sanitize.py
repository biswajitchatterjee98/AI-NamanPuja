import bleach

ALLOWED_TAGS = [
    "h1",
    "h2",
    "h3",
    "h4",
    "p",
    "ul",
    "ol",
    "li",
    "strong",
    "em",
    "a",
    "br",
]
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel"]}


def sanitize_html(content: str) -> str:
    return bleach.clean(
        content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
